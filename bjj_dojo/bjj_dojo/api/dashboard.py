# Copyright (c) 2024, Dojo Planner and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import today, add_days, add_months, flt


@frappe.whitelist()
def get_recommendations():
	"""Get recommended actions for the dashboard"""
	recommendations = []
	
	# New members who need follow-up (joined in last 7 days)
	recent_members = frappe.get_all("Dojo Member",
		filters={
			"join_date": [">=", add_days(today(), -7)],
			"status": "Active"
		},
		fields=["name", "member_name", "join_date", "email"],
		limit=3
	)
	
	for member in recent_members:
		recommendations.append({
			"title": f"Follow up with {member.member_name}",
			"description": "about their first visit",
			"action": f"view_member:{member.name}",
			"avatar": "/assets/bjj_dojo/images/avatar-placeholder.png",
			"priority": "high"
		})
	
	# Members with overdue payments
	overdue_members = frappe.get_all("Dojo Member",
		filters={
			"payment_status": "Overdue",
			"status": "Active"
		},
		fields=["name", "member_name", "outstanding_amount"],
		limit=5
	)
	
	if overdue_members:
		total_overdue = sum([flt(m.outstanding_amount) for m in overdue_members])
		recommendations.append({
			"title": "Resolve past due accounts.",
			"description": f"See {len(overdue_members)} members who are past due (${total_overdue:,.2f})",
			"action": "view_overdue_members",
			"icon": "fa-dollar",
			"priority": "medium"
		})
	
	# Members who haven't attended in 30 days
	inactive_members = frappe.db.sql("""
		SELECT dm.name, dm.member_name, MAX(ca.class_date) as last_attendance
		FROM `tabDojo Member` dm
		LEFT JOIN `tabClass Attendance` ca ON dm.name = ca.member AND ca.status = 'Present'
		WHERE dm.status = 'Active'
		GROUP BY dm.name, dm.member_name
		HAVING last_attendance < %s OR last_attendance IS NULL
		LIMIT 10
	""", add_days(today(), -30), as_dict=True)
	
	if inactive_members:
		recommendations.append({
			"title": "Set up automation email to follow up",
			"description": f"with {len(inactive_members)} past members who haven't attended recently",
			"action": "setup_email_automation",
			"icon": "fa-envelope",
			"priority": "low"
		})
	
	# Members eligible for belt promotion
	eligible_promotions = frappe.db.sql("""
		SELECT dm.name, dm.member_name, dm.current_belt,
			DATEDIFF(CURDATE(), COALESCE(dm.belt_promotion_date, dm.join_date)) / 30 as months_in_belt
		FROM `tabDojo Member` dm
		WHERE dm.status = 'Active'
			AND DATEDIFF(CURDATE(), COALESCE(dm.belt_promotion_date, dm.join_date)) / 30 >= 
				CASE dm.current_belt
					WHEN 'White' THEN 12
					WHEN 'Blue' THEN 24
					WHEN 'Purple' THEN 24
					WHEN 'Brown' THEN 12
					ELSE 36
				END
		LIMIT 5
	""", as_dict=True)
	
	for member in eligible_promotions:
		recommendations.append({
			"title": f"Consider promoting {member.member_name}",
			"description": f"from {member.current_belt} belt ({member.months_in_belt:.0f} months)",
			"action": f"view_promotion:{member.name}",
			"avatar": "/assets/bjj_dojo/images/avatar-placeholder.png",
			"priority": "medium"
		})
	
	return recommendations[:5]  # Return top 5 recommendations


@frappe.whitelist()
def get_recent_activity():
	"""Get recent member activity for the dashboard"""
	activities = []
	
	# Recent payments
	recent_payments = frappe.get_all("Dojo Payment",
		filters={
			"payment_date": [">=", add_days(today(), -7)],
			"status": "Completed"
		},
		fields=["member", "member_name", "amount", "payment_type", "payment_date"],
		order_by="payment_date desc",
		limit=5
	)
	
	for payment in recent_payments:
		activities.append({
			"member": payment.member,
			"member_name": payment.member_name,
			"description": f"has been charged ${payment.amount:,.2f} for {payment.payment_type.lower()}",
			"date": payment.payment_date,
			"type": "payment",
			"avatar": "/assets/bjj_dojo/images/avatar-placeholder.png"
		})
	
	# Recent membership cancellations
	cancelled_members = frappe.get_all("Dojo Member",
		filters={
			"status": "Inactive",
			"modified": [">=", add_days(today(), -7)]
		},
		fields=["name", "member_name", "next_payment_due", "modified"],
		order_by="modified desc",
		limit=3
	)
	
	for member in cancelled_members:
		activities.append({
			"member": member.name,
			"member_name": member.member_name,
			"description": f"cancelled their membership and it is expiring {member.next_payment_due or 'soon'}",
			"date": member.modified,
			"type": "cancellation",
			"avatar": "/assets/bjj_dojo/images/avatar-placeholder.png"
		})
	
	# Recent belt promotions
	recent_promotions = frappe.get_all("Belt Promotion",
		filters={
			"promotion_date": [">=", add_days(today(), -14)],
			"docstatus": 1
		},
		fields=["member", "member_name", "to_belt", "promotion_date"],
		order_by="promotion_date desc",
		limit=3
	)
	
	for promotion in recent_promotions:
		activities.append({
			"member": promotion.member,
			"member_name": promotion.member_name,
			"description": f"was promoted to {promotion.to_belt} belt",
			"date": promotion.promotion_date,
			"type": "promotion",
			"avatar": "/assets/bjj_dojo/images/avatar-placeholder.png"
		})
	
	# Recent merchandise purchases (if implemented)
	# This would be expanded when POS integration is added
	
	# Sort activities by date and return top 5
	activities.sort(key=lambda x: x['date'], reverse=True)
	return activities[:5]


@frappe.whitelist()
def get_dashboard_stats():
	"""Get key statistics for dashboard"""
	stats = {}
	
	# Member statistics
	stats['total_members'] = frappe.db.count("Dojo Member")
	stats['active_members'] = frappe.db.count("Dojo Member", {"status": "Active"})
	stats['new_members_this_month'] = frappe.db.count("Dojo Member", {
		"join_date": [">=", add_days(today(), -30)]
	})
	
	# Class statistics
	stats['classes_today'] = frappe.db.count("Dojo Class", {
		"class_date": today(),
		"status": ["!=", "Cancelled"]
	})
	stats['classes_this_week'] = frappe.db.count("Dojo Class", {
		"class_date": ["between", [add_days(today(), -7), today()]],
		"status": ["!=", "Cancelled"]
	})
	
	# Revenue statistics
	monthly_revenue = frappe.db.sql("""
		SELECT IFNULL(SUM(amount), 0) as total
		FROM `tabDojo Payment`
		WHERE payment_date >= %s 
			AND payment_date <= %s
			AND status = 'Completed'
	""", [add_days(today(), -30), today()])[0][0] or 0
	
	stats['monthly_revenue'] = monthly_revenue
	
	# Attendance statistics
	attendance_today = frappe.db.count("Class Attendance", {
		"class_date": today(),
		"status": "Present"
	})
	stats['attendance_today'] = attendance_today
	
	# Belt promotions this month
	stats['promotions_this_month'] = frappe.db.count("Belt Promotion", {
		"promotion_date": [">=", add_days(today(), -30)],
		"docstatus": 1
	})
	
	# Overdue payments
	stats['overdue_payments'] = frappe.db.count("Dojo Member", {
		"payment_status": "Overdue",
		"status": "Active"
	})
	
	return stats


@frappe.whitelist()
def get_earnings_trend(period="1year"):
	"""Get earnings trend data for charts"""
	if period == "1month":
		start_date = add_months(today(), -1)
		date_format = "%Y-%m-%d"
		group_by = "DATE(payment_date)"
	elif period == "3months":
		start_date = add_months(today(), -3)
		date_format = "%Y-%m-%d"
		group_by = "DATE(payment_date)"
	elif period == "6months":
		start_date = add_months(today(), -6)
		date_format = "%Y-%m"
		group_by = "DATE_FORMAT(payment_date, '%Y-%m')"
	else:  # 1year
		start_date = add_months(today(), -12)
		date_format = "%Y-%m"
		group_by = "DATE_FORMAT(payment_date, '%Y-%m')"
	
	earnings_data = frappe.db.sql(f"""
		SELECT 
			{group_by} as period,
			SUM(amount) as total_amount,
			COUNT(*) as transaction_count
		FROM `tabDojo Payment`
		WHERE payment_date >= %s 
			AND payment_date <= %s
			AND status = 'Completed'
		GROUP BY {group_by}
		ORDER BY period
	""", [start_date, today()], as_dict=True)
	
	return earnings_data


@frappe.whitelist()
def get_member_growth_trend(period="6months"):
	"""Get member growth trend data"""
	if period == "1month":
		start_date = add_months(today(), -1)
		group_by = "DATE(join_date)"
	elif period == "3months":
		start_date = add_months(today(), -3)
		group_by = "DATE(join_date)"
	else:  # 6months
		start_date = add_months(today(), -6)
		group_by = "DATE_FORMAT(join_date, '%Y-%m')"
	
	growth_data = frappe.db.sql(f"""
		SELECT 
			{group_by} as period,
			COUNT(*) as new_members
		FROM `tabDojo Member`
		WHERE join_date >= %s 
			AND join_date <= %s
		GROUP BY {group_by}
		ORDER BY period
	""", [start_date, today()], as_dict=True)
	
	# Calculate cumulative member count
	total_members_before = frappe.db.count("Dojo Member", {
		"join_date": ["<", start_date]
	})
	
	cumulative_count = total_members_before
	for data in growth_data:
		cumulative_count += data.new_members
		data['total_members'] = cumulative_count
	
	return growth_data


@frappe.whitelist()
def mark_recommendation_completed(recommendation_id):
	"""Mark a recommendation as completed"""
	# This would track completed recommendations
	# For now, just return success
	return {"status": "success", "message": "Recommendation marked as completed"}


@frappe.whitelist()
def get_quick_actions():
	"""Get quick action items for dashboard"""
	actions = []
	
	# Classes starting soon (next 2 hours)
	upcoming_classes = frappe.db.sql("""
		SELECT name, class_name, start_time, instructor
		FROM `tabDojo Class`
		WHERE class_date = %s
			AND start_time >= TIME(NOW())
			AND start_time <= TIME(DATE_ADD(NOW(), INTERVAL 2 HOUR))
			AND status = 'Scheduled'
		ORDER BY start_time
		LIMIT 3
	""", today(), as_dict=True)
	
	for cls in upcoming_classes:
		actions.append({
			"title": f"Class starting soon: {cls.class_name}",
			"description": f"at {cls.start_time} with {cls.instructor}",
			"action": f"view_class:{cls.name}",
			"type": "class",
			"urgency": "high"
		})
	
	# Members with birthdays today
	birthday_members = frappe.db.sql("""
		SELECT name, member_name
		FROM `tabDojo Member`
		WHERE status = 'Active'
			AND DAY(date_of_birth) = DAY(CURDATE())
			AND MONTH(date_of_birth) = MONTH(CURDATE())
		LIMIT 5
	""", as_dict=True)
	
	for member in birthday_members:
		actions.append({
			"title": f"Birthday: {member.member_name}",
			"description": "Send birthday wishes",
			"action": f"send_birthday_message:{member.name}",
			"type": "birthday",
			"urgency": "low"
		})
	
	return actions