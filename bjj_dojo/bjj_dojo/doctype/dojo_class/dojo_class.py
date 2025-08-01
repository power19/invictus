# Copyright (c) 2024, Dojo Planner and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import time_diff_in_seconds, flt, get_datetime
from datetime import datetime, timedelta


class DojoClass(Document):
	def validate(self):
		self.validate_times()
		self.calculate_duration()
		self.validate_capacity()
		
	def validate_times(self):
		"""Validate start and end times"""
		if self.start_time and self.end_time:
			if self.start_time >= self.end_time:
				frappe.throw("End time must be after start time")
	
	def calculate_duration(self):
		"""Calculate class duration in minutes"""
		if self.start_time and self.end_time:
			duration_seconds = time_diff_in_seconds(self.end_time, self.start_time)
			self.duration = int(duration_seconds / 60)
	
	def validate_capacity(self):
		"""Validate class capacity against attendance"""
		if self.max_capacity and self.attendance_count:
			if self.attendance_count > self.max_capacity:
				frappe.throw(f"Attendance count ({self.attendance_count}) cannot exceed max capacity ({self.max_capacity})")
	
	def on_update(self):
		"""Called after document is updated"""
		self.update_attendance_stats()
		
	def update_attendance_stats(self):
		"""Update attendance count and revenue"""
		# Get attendance count
		attendance_data = frappe.db.sql("""
			SELECT 
				COUNT(*) as total_attendees,
				COUNT(CASE WHEN member_type = 'Drop-in' THEN 1 END) as drop_ins,
				COUNT(CASE WHEN member_type = 'Member' THEN 1 END) as members
			FROM `tabClass Attendance`
			WHERE class = %s AND status = 'Present'
		""", self.name, as_dict=True)
		
		if attendance_data:
			data = attendance_data[0]
			self.attendance_count = data.total_attendees
			
			# Calculate revenue
			drop_in_revenue = flt(data.drop_ins) * flt(self.drop_in_fee or 0)
			member_revenue = flt(data.members) * flt(self.member_fee or 0)
			self.total_revenue = drop_in_revenue + member_revenue
			
			# Update without triggering validation again
			frappe.db.set_value("Dojo Class", self.name, {
				"attendance_count": self.attendance_count,
				"total_revenue": self.total_revenue
			}, update_modified=False)
	
	def get_attendance_list(self):
		"""Get list of attendees for this class"""
		return frappe.get_all("Class Attendance",
			filters={"class": self.name},
			fields=["member", "member_name", "status", "member_type", "check_in_time", "notes"],
			order_by="member_name"
		)
	
	def mark_attendance(self, member, status="Present", member_type="Member", notes=None):
		"""Mark attendance for a member"""
		# Check if attendance already exists
		existing = frappe.db.get_value("Class Attendance", 
			{"class": self.name, "member": member}, "name")
		
		if existing:
			# Update existing attendance
			attendance_doc = frappe.get_doc("Class Attendance", existing)
			attendance_doc.status = status
			attendance_doc.member_type = member_type
			if notes:
				attendance_doc.notes = notes
			attendance_doc.save()
		else:
			# Create new attendance record
			member_doc = frappe.get_doc("Dojo Member", member)
			attendance_doc = frappe.get_doc({
				"doctype": "Class Attendance",
				"class": self.name,
				"class_name": self.class_name,
				"member": member,
				"member_name": member_doc.member_name,
				"status": status,
				"member_type": member_type,
				"check_in_time": frappe.utils.now(),
				"notes": notes or ""
			})
			attendance_doc.insert()
		
		# Update class stats
		self.update_attendance_stats()
		return attendance_doc
	
	def get_class_schedule_conflicts(self):
		"""Check for scheduling conflicts with other classes"""
		if not self.class_date or not self.start_time or not self.end_time:
			return []
		
		conflicts = frappe.db.sql("""
			SELECT name, class_name, start_time, end_time, instructor
			FROM `tabDojo Class`
			WHERE name != %s 
				AND class_date = %s
				AND status NOT IN ('Cancelled', 'Completed')
				AND (
					(start_time <= %s AND end_time > %s) OR
					(start_time < %s AND end_time >= %s) OR
					(start_time >= %s AND end_time <= %s)
				)
		""", (self.name, self.class_date, self.start_time, self.start_time, 
			  self.end_time, self.end_time, self.start_time, self.end_time), as_dict=True)
		
		return conflicts
	
	def send_class_reminder(self):
		"""Send reminder to registered members"""
		if self.status != "Scheduled":
			return
		
		# Get members who attended recent classes of this type
		recent_attendees = frappe.db.sql("""
			SELECT DISTINCT ca.member, dm.email, dm.member_name
			FROM `tabClass Attendance` ca
			JOIN `tabDojo Class` dc ON ca.class = dc.name
			JOIN `tabDojo Member` dm ON ca.member = dm.name
			WHERE dc.class_type = %s 
				AND dc.class_date >= %s
				AND ca.status = 'Present'
				AND dm.status = 'Active'
				AND dm.email IS NOT NULL
		""", (self.class_type, frappe.utils.add_days(self.class_date, -30)), as_dict=True)
		
		# Send email reminders
		for attendee in recent_attendees:
			try:
				frappe.sendmail(
					recipients=[attendee.email],
					subject=f"Class Reminder: {self.class_name}",
					template="class_reminder",
					args={
						"member_name": attendee.member_name,
						"class_name": self.class_name,
						"class_date": self.class_date,
						"start_time": self.start_time,
						"instructor": self.instructor,
						"location": self.location or "Main Mat"
					}
				)
			except Exception as e:
				frappe.log_error(f"Failed to send reminder to {attendee.email}: {str(e)}")


@frappe.whitelist()
def get_class_dashboard_data(class_name):
	"""Get dashboard data for a specific class"""
	class_doc = frappe.get_doc("Dojo Class", class_name)
	
	return {
		"class_info": {
			"name": class_doc.class_name,
			"type": class_doc.class_type,
			"date": class_doc.class_date,
			"time": f"{class_doc.start_time} - {class_doc.end_time}",
			"instructor": class_doc.instructor,
			"status": class_doc.status,
			"capacity": class_doc.max_capacity,
			"attendance": class_doc.attendance_count
		},
		"attendance_list": class_doc.get_attendance_list(),
		"revenue": {
			"total": class_doc.total_revenue,
			"drop_in_fee": class_doc.drop_in_fee,
			"member_fee": class_doc.member_fee
		},
		"conflicts": class_doc.get_class_schedule_conflicts()
	}


@frappe.whitelist()
def get_weekly_schedule(start_date=None):
	"""Get weekly class schedule"""
	if not start_date:
		start_date = frappe.utils.today()
	
	end_date = frappe.utils.add_days(start_date, 6)
	
	classes = frappe.get_all("Dojo Class",
		filters={
			"class_date": ["between", [start_date, end_date]],
			"status": ["!=", "Cancelled"]
		},
		fields=["name", "class_name", "class_type", "class_date", "start_time", 
				"end_time", "instructor", "status", "attendance_count", "max_capacity"],
		order_by="class_date, start_time"
	)
	
	# Group by date
	schedule = {}
	for cls in classes:
		date_key = str(cls.class_date)
		if date_key not in schedule:
			schedule[date_key] = []
		schedule[date_key].append(cls)
	
	return schedule


@frappe.whitelist()
def mark_class_attendance(class_name, member, status="Present", member_type="Member", notes=None):
	"""Mark attendance for a member in a class"""
	class_doc = frappe.get_doc("Dojo Class", class_name)
	return class_doc.mark_attendance(member, status, member_type, notes)


@frappe.whitelist()
def get_instructor_schedule(instructor, start_date=None, end_date=None):
	"""Get schedule for a specific instructor"""
	if not start_date:
		start_date = frappe.utils.today()
	if not end_date:
		end_date = frappe.utils.add_days(start_date, 30)
	
	return frappe.get_all("Dojo Class",
		filters={
			"instructor": instructor,
			"class_date": ["between", [start_date, end_date]],
			"status": ["!=", "Cancelled"]
		},
		fields=["name", "class_name", "class_type", "class_date", "start_time", 
				"end_time", "status", "attendance_count", "total_revenue"],
		order_by="class_date, start_time"
	)