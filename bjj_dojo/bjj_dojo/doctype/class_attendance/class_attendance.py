# Copyright (c) 2024, Dojo Planner and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class ClassAttendance(Document):
	def validate(self):
		self.validate_duplicate_attendance()
		self.set_payment_details()
		
	def validate_duplicate_attendance(self):
		"""Prevent duplicate attendance records for same member and class"""
		existing = frappe.db.get_value("Class Attendance", 
			{
				"class": self.class_,
				"member": self.member,
				"name": ("!=", self.name)
			}, "name")
		
		if existing:
			frappe.throw(f"Attendance already marked for {self.member_name} in this class")
	
	def set_payment_details(self):
		"""Set payment details based on member type and class fees"""
		if not self.payment_required:
			self.payment_status = "Not Required"
			self.payment_amount = 0
			return
		
		# Get class details
		class_doc = frappe.get_doc("Dojo Class", self.class_)
		
		# Set payment amount based on member type
		if self.member_type == "Drop-in":
			self.payment_amount = class_doc.drop_in_fee or 0
		elif self.member_type == "Member":
			self.payment_amount = class_doc.member_fee or 0
		elif self.member_type == "Trial":
			self.payment_amount = 0  # Trial classes are usually free
			self.payment_status = "Waived"
		elif self.member_type == "Guest":
			self.payment_amount = class_doc.drop_in_fee or 0
		
		# Set default payment status
		if self.payment_status == "Not Required" and self.payment_amount > 0:
			self.payment_status = "Pending"
	
	def on_update(self):
		"""Called after document is updated"""
		# Update class attendance count
		self.update_class_stats()
		
		# Update member attendance stats
		self.update_member_stats()
	
	def update_class_stats(self):
		"""Update attendance count and revenue for the class"""
		class_doc = frappe.get_doc("Dojo Class", self.class_)
		class_doc.update_attendance_stats()
	
	def update_member_stats(self):
		"""Update member's attendance statistics"""
		if self.status == "Present":
			# Update member's last attendance date
			frappe.db.set_value("Dojo Member", self.member, 
				"last_attendance_date", self.class_date)
	
	def mark_payment_received(self, amount=None):
		"""Mark payment as received"""
		if not self.payment_required:
			frappe.throw("No payment required for this attendance")
		
		if amount:
			self.payment_amount = flt(amount)
		
		self.payment_status = "Paid"
		self.save()
		
		# Create payment record if needed
		self.create_payment_record()
	
	def create_payment_record(self):
		"""Create a payment record for this attendance"""
		if self.payment_status != "Paid" or not self.payment_amount:
			return
		
		# Check if payment record already exists
		existing_payment = frappe.db.get_value("Dojo Payment",
			{
				"member": self.member,
				"reference_doctype": "Class Attendance",
				"reference_name": self.name
			}, "name")
		
		if existing_payment:
			return existing_payment
		
		# Create new payment record
		payment_doc = frappe.get_doc({
			"doctype": "Dojo Payment",
			"member": self.member,
			"member_name": self.member_name,
			"payment_type": "Class Fee",
			"amount": self.payment_amount,
			"payment_date": frappe.utils.today(),
			"payment_method": "Cash",  # Default, can be updated
			"reference_doctype": "Class Attendance",
			"reference_name": self.name,
			"description": f"Payment for {self.class_name} on {self.class_date}",
			"status": "Completed"
		})
		payment_doc.insert()
		return payment_doc.name


@frappe.whitelist()
def bulk_mark_attendance(class_name, attendance_data):
	"""Bulk mark attendance for multiple members"""
	import json
	
	if isinstance(attendance_data, str):
		attendance_data = json.loads(attendance_data)
	
	results = []
	
	for data in attendance_data:
		try:
			# Check if attendance already exists
			existing = frappe.db.get_value("Class Attendance",
				{
					"class": class_name,
					"member": data.get("member")
				}, "name")
			
			if existing:
				# Update existing record
				attendance_doc = frappe.get_doc("Class Attendance", existing)
				attendance_doc.status = data.get("status", "Present")
				attendance_doc.member_type = data.get("member_type", "Member")
				attendance_doc.notes = data.get("notes", "")
				attendance_doc.save()
			else:
				# Create new record
				member_doc = frappe.get_doc("Dojo Member", data.get("member"))
				attendance_doc = frappe.get_doc({
					"doctype": "Class Attendance",
					"class": class_name,
					"member": data.get("member"),
					"member_name": member_doc.member_name,
					"status": data.get("status", "Present"),
					"member_type": data.get("member_type", "Member"),
					"notes": data.get("notes", "")
				})
				attendance_doc.insert()
			
			results.append({
				"member": data.get("member"),
				"status": "success",
				"attendance_id": attendance_doc.name
			})
			
		except Exception as e:
			results.append({
				"member": data.get("member"),
				"status": "error",
				"error": str(e)
			})
	
	return results


@frappe.whitelist()
def get_class_attendance_summary(class_name):
	"""Get attendance summary for a class"""
	attendance_data = frappe.db.sql("""
		SELECT 
			status,
			member_type,
			COUNT(*) as count,
			SUM(CASE WHEN payment_required = 1 AND payment_status = 'Paid' THEN payment_amount ELSE 0 END) as revenue
		FROM `tabClass Attendance`
		WHERE class = %s
		GROUP BY status, member_type
	""", class_name, as_dict=True)
	
	# Get total counts
	total_registered = frappe.db.count("Class Attendance", {"class": class_name})
	total_present = frappe.db.count("Class Attendance", {"class": class_name, "status": "Present"})
	total_revenue = frappe.db.sql("""
		SELECT SUM(CASE WHEN payment_required = 1 AND payment_status = 'Paid' THEN payment_amount ELSE 0 END)
		FROM `tabClass Attendance`
		WHERE class = %s
	""", class_name)[0][0] or 0
	
	return {
		"attendance_breakdown": attendance_data,
		"summary": {
			"total_registered": total_registered,
			"total_present": total_present,
			"attendance_rate": (total_present / total_registered * 100) if total_registered > 0 else 0,
			"total_revenue": total_revenue
		}
	}


@frappe.whitelist()
def get_member_attendance_history(member, limit=50):
	"""Get attendance history for a member"""
	return frappe.get_all("Class Attendance",
		filters={"member": member},
		fields=["class", "class_name", "class_date", "status", "member_type", 
				"check_in_time", "payment_amount", "payment_status", "notes"],
		order_by="class_date desc",
		limit=limit
	)


@frappe.whitelist()
def get_attendance_analytics(start_date=None, end_date=None):
	"""Get attendance analytics for reporting"""
	conditions = []
	params = []
	
	if start_date:
		conditions.append("ca.class_date >= %s")
		params.append(start_date)
	
	if end_date:
		conditions.append("ca.class_date <= %s")
		params.append(end_date)
	
	where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
	
	# Attendance by class type
	class_type_stats = frappe.db.sql(f"""
		SELECT 
			dc.class_type,
			COUNT(ca.name) as total_attendance,
			COUNT(CASE WHEN ca.status = 'Present' THEN 1 END) as present_count,
			AVG(CASE WHEN ca.status = 'Present' THEN 1 ELSE 0 END) * 100 as attendance_rate
		FROM `tabClass Attendance` ca
		JOIN `tabDojo Class` dc ON ca.class = dc.name
		{where_clause}
		GROUP BY dc.class_type
		ORDER BY total_attendance DESC
	""", params, as_dict=True)
	
	# Member type distribution
	member_type_stats = frappe.db.sql(f"""
		SELECT 
			ca.member_type,
			COUNT(ca.name) as count,
			SUM(CASE WHEN ca.payment_required = 1 AND ca.payment_status = 'Paid' THEN ca.payment_amount ELSE 0 END) as revenue
		FROM `tabClass Attendance` ca
		JOIN `tabDojo Class` dc ON ca.class = dc.name
		{where_clause}
		GROUP BY ca.member_type
	""", params, as_dict=True)
	
	# Daily attendance trends
	daily_trends = frappe.db.sql(f"""
		SELECT 
			ca.class_date,
			COUNT(ca.name) as total_registered,
			COUNT(CASE WHEN ca.status = 'Present' THEN 1 END) as present_count
		FROM `tabClass Attendance` ca
		JOIN `tabDojo Class` dc ON ca.class = dc.name
		{where_clause}
		GROUP BY ca.class_date
		ORDER BY ca.class_date
	""", params, as_dict=True)
	
	return {
		"class_type_stats": class_type_stats,
		"member_type_stats": member_type_stats,
		"daily_trends": daily_trends
	}