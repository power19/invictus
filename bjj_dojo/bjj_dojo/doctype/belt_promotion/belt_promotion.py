# Copyright (c) 2024, Dojo Planner and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import today, date_diff, getdate


class BeltPromotion(Document):
	def validate(self):
		self.validate_belt_progression()
		self.calculate_time_in_belt()
		self.validate_promotion_date()
		
	def validate_belt_progression(self):
		"""Validate that belt promotion follows proper sequence"""
		belt_order = ["White", "Blue", "Purple", "Brown", "Black", "Coral", "Red"]
		
		if self.from_belt and self.to_belt:
			from_index = belt_order.index(self.from_belt)
			to_index = belt_order.index(self.to_belt)
			
			if to_index <= from_index:
				frappe.throw(f"Cannot promote from {self.from_belt} to {self.to_belt}. Belt promotion must be progressive.")
			
			if to_index - from_index > 1:
				frappe.throw(f"Cannot skip belt levels. Must promote from {self.from_belt} to {belt_order[from_index + 1]} first.")
	
	def calculate_time_in_belt(self):
		"""Calculate time spent in previous belt"""
		if not self.member:
			return
			
		member_doc = frappe.get_doc("Dojo Member", self.member)
		
		if member_doc.belt_promotion_date:
			# Calculate months since last promotion
			months = date_diff(self.promotion_date, member_doc.belt_promotion_date) / 30
			self.time_in_previous_belt = int(months)
		else:
			# Calculate months since joining (first belt)
			if member_doc.join_date:
				months = date_diff(self.promotion_date, member_doc.join_date) / 30
				self.time_in_previous_belt = int(months)
	
	def validate_promotion_date(self):
		"""Validate promotion date"""
		if self.promotion_date and getdate(self.promotion_date) > getdate(today()):
			frappe.throw("Promotion date cannot be in the future")
	
	def on_submit(self):
		"""Update member's belt information when promotion is submitted"""
		self.update_member_belt()
		self.send_promotion_notification()
	
	def on_cancel(self):
		"""Revert member's belt when promotion is cancelled"""
		member_doc = frappe.get_doc("Dojo Member", self.member)
		member_doc.current_belt = self.from_belt
		
		# Find previous promotion date
		previous_promotion = frappe.get_all("Belt Promotion",
			filters={
				"member": self.member,
				"docstatus": 1,
				"promotion_date": ["<", self.promotion_date]
			},
			fields=["promotion_date"],
			order_by="promotion_date desc",
			limit=1
		)
		
		if previous_promotion:
			member_doc.belt_promotion_date = previous_promotion[0].promotion_date
		else:
			member_doc.belt_promotion_date = None
		
		member_doc.save()
	
	def update_member_belt(self):
		"""Update member's current belt and promotion date"""
		member_doc = frappe.get_doc("Dojo Member", self.member)
		member_doc.current_belt = self.to_belt
		member_doc.belt_promotion_date = self.promotion_date
		member_doc.save()
	
	def send_promotion_notification(self):
		"""Send congratulations email to member"""
		member_doc = frappe.get_doc("Dojo Member", self.member)
		
		if not member_doc.email:
			return
		
		try:
			frappe.sendmail(
				recipients=[member_doc.email],
				subject=f"Congratulations on your {self.to_belt} Belt Promotion!",
				template="belt_promotion_congratulations",
				args={
					"member_name": member_doc.member_name,
					"from_belt": self.from_belt,
					"to_belt": self.to_belt,
					"promotion_date": self.promotion_date,
					"instructor": self.instructor,
					"notes": self.notes,
					"dojo_name": frappe.defaults.get_user_default("Company") or "BJJ Dojo"
				}
			)
		except Exception as e:
			frappe.log_error(f"Failed to send promotion notification to {member_doc.email}: {str(e)}")
	
	def generate_certificate(self):
		"""Generate promotion certificate"""
		# This would generate a PDF certificate
		# For now, we'll mark it as issued
		self.certificate_issued = 1
		self.save()
		
		return "Certificate generated successfully"


@frappe.whitelist()
def get_promotion_eligibility(member):
	"""Check if member is eligible for promotion"""
	member_doc = frappe.get_doc("Dojo Member", member)
	
	# Get current belt requirements
	requirements = get_belt_requirements(member_doc.current_belt)
	
	# Calculate time in current belt
	time_in_belt = 0
	if member_doc.belt_promotion_date:
		time_in_belt = date_diff(today(), member_doc.belt_promotion_date) / 30
	elif member_doc.join_date:
		time_in_belt = date_diff(today(), member_doc.join_date) / 30
	
	# Get attendance stats
	attendance_stats = member_doc.get_attendance_stats()
	
	# Check eligibility
	eligible = True
	reasons = []
	
	if time_in_belt < requirements.get("min_time_months", 0):
		eligible = False
		reasons.append(f"Minimum time requirement not met ({time_in_belt:.1f} months, need {requirements['min_time_months']})")
	
	if attendance_stats["total_classes"] < requirements.get("min_classes", 0):
		eligible = False
		reasons.append(f"Minimum class attendance not met ({attendance_stats['total_classes']} classes, need {requirements['min_classes']})")
	
	if attendance_stats["attendance_rate"] < requirements.get("min_attendance_rate", 0):
		eligible = False
		reasons.append(f"Attendance rate too low ({attendance_stats['attendance_rate']:.1f}%, need {requirements['min_attendance_rate']}%)")
	
	return {
		"eligible": eligible,
		"reasons": reasons,
		"current_belt": member_doc.current_belt,
		"time_in_belt": time_in_belt,
		"attendance_stats": attendance_stats,
		"requirements": requirements
	}


def get_belt_requirements(current_belt):
	"""Get promotion requirements for current belt"""
	requirements = {
		"White": {
			"min_time_months": 12,
			"min_classes": 100,
			"min_attendance_rate": 70,
			"next_belt": "Blue"
		},
		"Blue": {
			"min_time_months": 24,
			"min_classes": 200,
			"min_attendance_rate": 75,
			"next_belt": "Purple"
		},
		"Purple": {
			"min_time_months": 24,
			"min_classes": 300,
			"min_attendance_rate": 80,
			"next_belt": "Brown"
		},
		"Brown": {
			"min_time_months": 12,
			"min_classes": 200,
			"min_attendance_rate": 85,
			"next_belt": "Black"
		},
		"Black": {
			"min_time_months": 36,
			"min_classes": 500,
			"min_attendance_rate": 90,
			"next_belt": "Coral"
		}
	}
	
	return requirements.get(current_belt, {})


@frappe.whitelist()
def get_promotion_history(member=None, limit=50):
	"""Get promotion history for member or all members"""
	filters = {"docstatus": 1}
	if member:
		filters["member"] = member
	
	return frappe.get_all("Belt Promotion",
		filters=filters,
		fields=["name", "member", "member_name", "from_belt", "to_belt", 
				"promotion_date", "instructor", "time_in_previous_belt"],
		order_by="promotion_date desc",
		limit=limit
	)


@frappe.whitelist()
def get_belt_statistics():
	"""Get belt distribution statistics"""
	# Current belt distribution
	belt_distribution = frappe.db.sql("""
		SELECT current_belt, COUNT(*) as count
		FROM `tabDojo Member`
		WHERE status = 'Active'
		GROUP BY current_belt
		ORDER BY FIELD(current_belt, 'White', 'Blue', 'Purple', 'Brown', 'Black', 'Coral', 'Red')
	""", as_dict=True)
	
	# Promotions this year
	promotions_this_year = frappe.db.sql("""
		SELECT 
			to_belt,
			COUNT(*) as count,
			MONTH(promotion_date) as month
		FROM `tabBelt Promotion`
		WHERE YEAR(promotion_date) = YEAR(CURDATE())
			AND docstatus = 1
		GROUP BY to_belt, MONTH(promotion_date)
		ORDER BY month, FIELD(to_belt, 'White', 'Blue', 'Purple', 'Brown', 'Black', 'Coral', 'Red')
	""", as_dict=True)
	
	# Average time between promotions
	avg_promotion_time = frappe.db.sql("""
		SELECT 
			to_belt,
			AVG(time_in_previous_belt) as avg_months
		FROM `tabBelt Promotion`
		WHERE docstatus = 1 AND time_in_previous_belt > 0
		GROUP BY to_belt
		ORDER BY FIELD(to_belt, 'Blue', 'Purple', 'Brown', 'Black', 'Coral', 'Red')
	""", as_dict=True)
	
	return {
		"belt_distribution": belt_distribution,
		"promotions_this_year": promotions_this_year,
		"avg_promotion_time": avg_promotion_time
	}


@frappe.whitelist()
def bulk_promote_members(promotions_data):
	"""Bulk promote multiple members"""
	import json
	
	if isinstance(promotions_data, str):
		promotions_data = json.loads(promotions_data)
	
	results = []
	
	for promotion in promotions_data:
		try:
			# Create promotion record
			promotion_doc = frappe.get_doc({
				"doctype": "Belt Promotion",
				"member": promotion.get("member"),
				"to_belt": promotion.get("to_belt"),
				"promotion_date": promotion.get("promotion_date", today()),
				"instructor": promotion.get("instructor"),
				"notes": promotion.get("notes", ""),
				"requirements_met": 1
			})
			
			promotion_doc.insert()
			promotion_doc.submit()
			
			results.append({
				"member": promotion.get("member"),
				"status": "success",
				"promotion_id": promotion_doc.name
			})
			
		except Exception as e:
			results.append({
				"member": promotion.get("member"),
				"status": "error",
				"error": str(e)
			})
	
	return results