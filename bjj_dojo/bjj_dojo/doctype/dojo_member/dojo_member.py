# Copyright (c) 2024, Dojo Planner and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import today, add_months, flt
from datetime import datetime, timedelta


class DojoMember(Document):
	def validate(self):
		self.validate_email()
		self.calculate_outstanding_amount()
		self.set_next_payment_due()
		
	def validate_email(self):
		"""Validate email format and uniqueness"""
		if self.email:
			# Check if email already exists for another member
			existing = frappe.db.get_value("Dojo Member", 
				{"email": self.email, "name": ("!=", self.name)}, "name")
			if existing:
				frappe.throw(f"Email {self.email} already exists for another member")
	
	def calculate_outstanding_amount(self):
		"""Calculate outstanding amount based on payments"""
		if not self.monthly_fee:
			self.outstanding_amount = 0
			return
			
		# Get total payments made
		total_payments = frappe.db.sql("""
			SELECT IFNULL(SUM(amount), 0) as total
			FROM `tabDojo Payment`
			WHERE member = %s AND docstatus = 1
		""", self.name)[0][0] or 0
		
		self.total_paid = total_payments
		
		# Calculate expected payments based on membership duration
		if self.join_date:
			months_since_joining = self.get_months_since_joining()
			expected_total = flt(self.monthly_fee) * months_since_joining
			self.outstanding_amount = max(0, expected_total - total_payments)
	
	def get_months_since_joining(self):
		"""Calculate months since joining"""
		if not self.join_date:
			return 0
			
		join_date = datetime.strptime(str(self.join_date), '%Y-%m-%d')
		today_date = datetime.now()
		
		months = (today_date.year - join_date.year) * 12 + (today_date.month - join_date.month)
		return max(1, months)  # At least 1 month
	
	def set_next_payment_due(self):
		"""Set next payment due date"""
		if not self.last_payment_date or not self.monthly_fee:
			if self.join_date:
				self.next_payment_due = add_months(self.join_date, 1)
			return
			
		self.next_payment_due = add_months(self.last_payment_date, 1)
	
	def update_payment_status(self):
		"""Update payment status based on outstanding amount and due date"""
		if not self.next_payment_due:
			return
			
		today_date = datetime.strptime(today(), '%Y-%m-%d')
		due_date = datetime.strptime(str(self.next_payment_due), '%Y-%m-%d')
		
		if self.outstanding_amount <= 0:
			self.payment_status = "Paid"
		elif today_date > due_date:
			self.payment_status = "Overdue"
		elif today_date >= due_date - timedelta(days=7):
			self.payment_status = "Pending"
		else:
			self.payment_status = "Paid"
	
	def on_update(self):
		"""Called after document is updated"""
		self.update_payment_status()
		
	def get_attendance_stats(self):
		"""Get member attendance statistics"""
		stats = frappe.db.sql("""
			SELECT 
				COUNT(*) as total_classes,
				COUNT(CASE WHEN status = 'Present' THEN 1 END) as attended,
				COUNT(CASE WHEN status = 'Absent' THEN 1 END) as missed
			FROM `tabClass Attendance`
			WHERE member = %s
		""", self.name, as_dict=True)
		
		if stats:
			stat = stats[0]
			stat['attendance_rate'] = (stat['attended'] / stat['total_classes'] * 100) if stat['total_classes'] > 0 else 0
			return stat
		
		return {'total_classes': 0, 'attended': 0, 'missed': 0, 'attendance_rate': 0}
	
	def get_belt_progression_history(self):
		"""Get belt progression history"""
		return frappe.get_all("Belt Promotion", 
			filters={"member": self.name},
			fields=["promotion_date", "from_belt", "to_belt", "instructor", "notes"],
			order_by="promotion_date desc"
		)
	
	def promote_belt(self, new_belt, instructor, notes=None):
		"""Promote member to new belt"""
		# Create belt promotion record
		promotion = frappe.get_doc({
			"doctype": "Belt Promotion",
			"member": self.name,
			"member_name": self.member_name,
			"from_belt": self.current_belt,
			"to_belt": new_belt,
			"promotion_date": today(),
			"instructor": instructor,
			"notes": notes or ""
		})
		promotion.insert()
		
		# Update member's current belt
		self.current_belt = new_belt
		self.belt_promotion_date = today()
		self.save()
		
		return promotion


@frappe.whitelist()
def get_member_dashboard_data(member):
	"""Get dashboard data for a specific member"""
	member_doc = frappe.get_doc("Dojo Member", member)
	
	return {
		"member_info": {
			"name": member_doc.member_name,
			"status": member_doc.status,
			"belt": member_doc.current_belt,
			"join_date": member_doc.join_date,
			"membership_type": member_doc.membership_type
		},
		"payment_info": {
			"monthly_fee": member_doc.monthly_fee,
			"payment_status": member_doc.payment_status,
			"outstanding_amount": member_doc.outstanding_amount,
			"total_paid": member_doc.total_paid,
			"next_payment_due": member_doc.next_payment_due
		},
		"attendance_stats": member_doc.get_attendance_stats(),
		"belt_history": member_doc.get_belt_progression_history()
	}


@frappe.whitelist()
def get_members_summary():
	"""Get summary statistics for all members"""
	total_members = frappe.db.count("Dojo Member")
	active_members = frappe.db.count("Dojo Member", {"status": "Active"})
	
	# Belt distribution
	belt_distribution = frappe.db.sql("""
		SELECT current_belt, COUNT(*) as count
		FROM `tabDojo Member`
		WHERE status = 'Active'
		GROUP BY current_belt
		ORDER BY FIELD(current_belt, 'White', 'Blue', 'Purple', 'Brown', 'Black', 'Coral', 'Red')
	""", as_dict=True)
	
	# Payment status distribution
	payment_status = frappe.db.sql("""
		SELECT payment_status, COUNT(*) as count
		FROM `tabDojo Member`
		WHERE status = 'Active'
		GROUP BY payment_status
	""", as_dict=True)
	
	# Monthly revenue
	monthly_revenue = frappe.db.sql("""
		SELECT IFNULL(SUM(monthly_fee), 0) as total
		FROM `tabDojo Member`
		WHERE status = 'Active' AND monthly_fee IS NOT NULL
	""")[0][0] or 0
	
	return {
		"total_members": total_members,
		"active_members": active_members,
		"belt_distribution": belt_distribution,
		"payment_status": payment_status,
		"monthly_revenue": monthly_revenue
	}