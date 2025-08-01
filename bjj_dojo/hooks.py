from . import __version__ as app_version

app_name = "bjj_dojo"
app_title = "BJJ Dojo Management"
app_publisher = "Dojo Planner"
app_description = "Complete Brazilian Jiu-Jitsu dojo management system for ERPNext"
app_icon = "octicon octicon-organization"
app_color = "grey"
app_email = "admin@dojoplanner.com"
app_license = "MIT"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/bjj_dojo/css/bjj_dojo.css"
# app_include_js = "/assets/bjj_dojo/js/bjj_dojo.js"

# include js, css files in header of web template
# web_include_css = "/assets/bjj_dojo/css/bjj_dojo.css"
# web_include_js = "/assets/bjj_dojo/js/bjj_dojo.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "bjj_dojo/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "bjj_dojo.install.before_install"
after_install = "bjj_dojo.bjj_dojo.install.after_install"

# Uninstallation
# ------------

before_uninstall = "bjj_dojo.bjj_dojo.install.before_uninstall"
# after_uninstall = "bjj_dojo.uninstall.after_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "bjj_dojo.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
#	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
#	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
#	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
#	"*": {
#		"on_update": "method",
#		"on_cancel": "method",
#		"on_trash": "method"
#	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
#	"all": [
#		"bjj_dojo.tasks.all"
#	],
#	"daily": [
#		"bjj_dojo.tasks.daily"
#	],
#	"hourly": [
#		"bjj_dojo.tasks.hourly"
#	],
#	"weekly": [
#		"bjj_dojo.tasks.weekly"
#	]
#	"monthly": [
#		"bjj_dojo.tasks.monthly"
#	]
# }

# Testing
# -------

# before_tests = "bjj_dojo.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
#	"frappe.desk.doctype.event.event.get_events": "bjj_dojo.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
#	"Task": "bjj_dojo.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]


# User Data Protection
# --------------------

user_data_fields = [
	{
		"doctype": "{doctype_1}",
		"filter_by": "{filter_by}",
		"redact_fields": ["{field_1}", "{field_2}"],
		"partial": 1,
	},
	{
		"doctype": "{doctype_2}",
		"filter_by": "{filter_by}",
		"partial": 1,
	},
	{
		"doctype": "{doctype_3}",
		"strict": False,
	},
	{
		"doctype": "{doctype_4}"
	}
]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
#	"bjj_dojo.auth.validate"
# ]

# Translation
# --------------------------------

# Make link fields search translated document names for these DocTypes
# Recommended only for DocTypes which have limited documents with untranslated names
# For example: Role, Gender, etc.
# translated_search_doctypes = []

# Workspaces
# ----------

# List of workspaces that should be created for this app
# Each workspace is a dictionary with the following keys:
# - name: Name of the workspace
# - label: Label of the workspace
# - icon: Icon of the workspace
# - color: Color of the workspace
# - is_standard: Whether the workspace is standard or not
# - parent_page: Parent page of the workspace
# - public: Whether the workspace is public or not
# - content: Content of the workspace

workspaces = [
	{
		"name": "BJJ Dojo",
		"label": "BJJ Dojo",
		"icon": "octicon octicon-organization",
		"color": "grey",
		"is_standard": 1,
		"parent_page": "",
		"public": 1,
		"content": '[{"type": "card", "data": {"card_name": "Dojo Dashboard", "col": 12}}]'
	}
]