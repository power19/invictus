# Copyright (c) 2024, Dojo Planner and contributors
# For license information, please see license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def after_install():
	"""Called after app installation"""
	create_custom_roles()
	create_custom_fields_for_integration()
	create_default_settings()
	setup_email_templates()
	frappe.db.commit()


def create_custom_roles():
	"""Create custom roles for BJJ Dojo"""
	roles = [
		{
			"role_name": "Dojo Manager",
			"desk_access": 1,
			"home_page": "dojo_dashboard"
		},
		{
			"role_name": "Dojo Instructor", 
			"desk_access": 1,
			"home_page": "dojo_dashboard"
		},
		{
			"role_name": "Dojo Staff",
			"desk_access": 1,
			"home_page": "dojo_dashboard"
		},
		{
			"role_name": "Dojo Member",
			"desk_access": 0
		}
	]
	
	for role_data in roles:
		if not frappe.db.exists("Role", role_data["role_name"]):
			role = frappe.get_doc({
				"doctype": "Role",
				"role_name": role_data["role_name"],
				"desk_access": role_data["desk_access"],
				"home_page": role_data.get("home_page", ""),
				"is_custom": 1
			})
			role.insert(ignore_permissions=True)


def create_custom_fields_for_integration():
	"""Create custom fields for ERPNext integration"""
	
	# Add custom field to Customer for linking to Dojo Member
	custom_fields = {
		"Customer": [
			{
				"fieldname": "custom_dojo_member",
				"label": "Dojo Member",
				"fieldtype": "Link",
				"options": "Dojo Member",
				"insert_after": "customer_name"
			}
		],
		"User": [
			{
				"fieldname": "custom_dojo_member",
				"label": "Dojo Member",
				"fieldtype": "Link", 
				"options": "Dojo Member",
				"insert_after": "email"
			},
			{
				"fieldname": "custom_instructor_profile",
				"label": "Instructor Profile",
				"fieldtype": "Section Break",
				"insert_after": "custom_dojo_member"
			},
			{
				"fieldname": "custom_belt_rank",
				"label": "Belt Rank",
				"fieldtype": "Select",
				"options": "White\nBlue\nPurple\nBrown\nBlack\nCoral\nRed",
				"insert_after": "custom_instructor_profile"
			},
			{
				"fieldname": "custom_specialties",
				"label": "Specialties",
				"fieldtype": "Text",
				"insert_after": "custom_belt_rank"
			}
		]
	}
	
	create_custom_fields(custom_fields)


def create_default_settings():
	"""Create default settings for the dojo"""
	
	# Create default customer group for dojo members
	if not frappe.db.exists("Customer Group", "Dojo Members"):
		customer_group = frappe.get_doc({
			"doctype": "Customer Group",
			"customer_group_name": "Dojo Members",
			"parent_customer_group": "All Customer Groups",
			"is_group": 0
		})
		customer_group.insert(ignore_permissions=True)
	
	# Create default accounts for dojo operations
	company = frappe.defaults.get_user_default("Company")
	if company:
		accounts_to_create = [
			{
				"account_name": "Membership Income",
				"account_type": "Income Account",
				"root_type": "Income"
			},
			{
				"account_name": "Class Fee Income", 
				"account_type": "Income Account",
				"root_type": "Income"
			},
			{
				"account_name": "Private Lesson Income",
				"account_type": "Income Account", 
				"root_type": "Income"
			},
			{
				"account_name": "Payment Processing Fees",
				"account_type": "Expense Account",
				"root_type": "Expense"
			}
		]
		
		for account_data in accounts_to_create:
			account_name = f"{account_data['account_name']} - {company}"
			if not frappe.db.exists("Account", account_name):
				try:
					account = frappe.get_doc({
						"doctype": "Account",
						"account_name": account_data["account_name"],
						"company": company,
						"account_type": account_data["account_type"],
						"root_type": account_data["root_type"],
						"is_group": 0,
						"parent_account": f"{account_data['root_type']} - {company}"
					})
					account.insert(ignore_permissions=True)
				except Exception as e:
					frappe.log_error(f"Failed to create account {account_name}: {str(e)}")


def setup_email_templates():
	"""Create email templates for dojo communications"""
	
	templates = [
		{
			"name": "Welcome New Member",
			"subject": "Welcome to {{ dojo_name }}!",
			"response": """
			<p>Dear {{ member_name }},</p>
			
			<p>Welcome to {{ dojo_name }}! We're excited to have you join our Brazilian Jiu-Jitsu family.</p>
			
			<p>Here are some important details for your first classes:</p>
			<ul>
				<li>Please arrive 15 minutes early for your first class</li>
				<li>Bring a water bottle and towel</li>
				<li>Wear comfortable athletic clothing</li>
				<li>We'll provide a loaner gi for your first few classes</li>
			</ul>
			
			<p>If you have any questions, please don't hesitate to contact us.</p>
			
			<p>See you on the mats!</p>
			<p>{{ dojo_name }} Team</p>
			"""
		},
		{
			"name": "Belt Promotion Congratulations",
			"subject": "Congratulations on your {{ to_belt }} Belt!",
			"response": """
			<p>Dear {{ member_name }},</p>
			
			<p>Congratulations on your promotion to {{ to_belt }} belt!</p>
			
			<p>This achievement represents your dedication, hard work, and growth in Brazilian Jiu-Jitsu. 
			Your promotion from {{ from_belt }} to {{ to_belt }} belt on {{ promotion_date }} is well-deserved.</p>
			
			{% if notes %}
			<p>{{ instructor }} notes: {{ notes }}</p>
			{% endif %}
			
			<p>We're proud of your progress and look forward to seeing your continued development on the mats.</p>
			
			<p>Congratulations again!</p>
			<p>{{ dojo_name }} Team</p>
			"""
		},
		{
			"name": "Payment Receipt",
			"subject": "Payment Receipt - {{ payment.receipt_number }}",
			"response": """
			<p>Dear {{ member_name }},</p>
			
			<p>Thank you for your payment. Here are the details:</p>
			
			<table style="border-collapse: collapse; width: 100%;">
				<tr>
					<td style="border: 1px solid #ddd; padding: 8px;"><strong>Receipt Number:</strong></td>
					<td style="border: 1px solid #ddd; padding: 8px;">{{ payment.receipt_number }}</td>
				</tr>
				<tr>
					<td style="border: 1px solid #ddd; padding: 8px;"><strong>Payment Type:</strong></td>
					<td style="border: 1px solid #ddd; padding: 8px;">{{ payment.payment_type }}</td>
				</tr>
				<tr>
					<td style="border: 1px solid #ddd; padding: 8px;"><strong>Amount:</strong></td>
					<td style="border: 1px solid #ddd; padding: 8px;">${{ payment.amount }}</td>
				</tr>
				<tr>
					<td style="border: 1px solid #ddd; padding: 8px;"><strong>Payment Date:</strong></td>
					<td style="border: 1px solid #ddd; padding: 8px;">{{ payment.payment_date }}</td>
				</tr>
				<tr>
					<td style="border: 1px solid #ddd; padding: 8px;"><strong>Payment Method:</strong></td>
					<td style="border: 1px solid #ddd; padding: 8px;">{{ payment.payment_method }}</td>
				</tr>
			</table>
			
			<p>Thank you for being part of {{ dojo_name }}!</p>
			<p>{{ dojo_name }} Team</p>
			"""
		},
		{
			"name": "Class Reminder",
			"subject": "Class Reminder: {{ class_name }}",
			"response": """
			<p>Dear {{ member_name }},</p>
			
			<p>This is a reminder about your upcoming class:</p>
			
			<p><strong>{{ class_name }}</strong><br>
			Date: {{ class_date }}<br>
			Time: {{ start_time }}<br>
			Instructor: {{ instructor }}<br>
			Location: {{ location }}</p>
			
			<p>We look forward to seeing you on the mats!</p>
			
			<p>{{ dojo_name }} Team</p>
			"""
		}
	]
	
	for template_data in templates:
		if not frappe.db.exists("Email Template", template_data["name"]):
			try:
				template = frappe.get_doc({
					"doctype": "Email Template",
					"name": template_data["name"],
					"subject": template_data["subject"],
					"response": template_data["response"],
					"use_html": 1
				})
				template.insert(ignore_permissions=True)
			except Exception as e:
				frappe.log_error(f"Failed to create email template {template_data['name']}: {str(e)}")


def before_uninstall():
	"""Called before app uninstallation"""
	# Clean up custom fields and roles if needed
	pass