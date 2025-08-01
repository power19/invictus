# Copyright (c) 2024, Dojo Planner and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, today, add_months


class DojoPayment(Document):
	def validate(self):
		self.calculate_net_amount()
		self.validate_amount()
		self.set_receipt_number()
		
	def calculate_net_amount(self):
		"""Calculate net amount after processing fees"""
		self.net_amount = flt(self.amount) - flt(self.processing_fee or 0)
	
	def validate_amount(self):
		"""Validate payment amount"""
		if flt(self.amount) <= 0:
			frappe.throw("Payment amount must be greater than zero")
		
		if flt(self.processing_fee or 0) >= flt(self.amount):
			frappe.throw("Processing fee cannot be greater than or equal to payment amount")
	
	def set_receipt_number(self):
		"""Generate receipt number if not set"""
		if not self.receipt_number and self.status == "Completed":
			# Generate receipt number based on naming series and current count
			count = frappe.db.count("Dojo Payment", {"status": "Completed"}) + 1
			self.receipt_number = f"RCP-{count:06d}"
	
	def on_submit(self):
		"""Called when payment is submitted"""
		self.status = "Completed"
		self.update_member_payment_info()
		self.create_accounting_entries()
	
	def on_cancel(self):
		"""Called when payment is cancelled"""
		self.status = "Cancelled"
		self.update_member_payment_info()
	
	def update_member_payment_info(self):
		"""Update member's payment information"""
		if self.payment_type in ["Monthly Membership", "Annual Membership"]:
			member_doc = frappe.get_doc("Dojo Member", self.member)
			
			if self.status == "Completed":
				# Update last payment date
				member_doc.last_payment_date = self.payment_date
				
				# Calculate next payment due date
				if self.payment_type == "Monthly Membership":
					member_doc.next_payment_due = add_months(self.payment_date, 1)
				elif self.payment_type == "Annual Membership":
					member_doc.next_payment_due = add_months(self.payment_date, 12)
				
				# Update payment status
				member_doc.payment_status = "Paid"
			
			member_doc.save()
	
	def create_accounting_entries(self):
		"""Create accounting entries for the payment"""
		if self.status != "Completed":
			return
		
		# This would integrate with ERPNext's accounting system
		# For now, we'll create a simple journal entry structure
		
		try:
			# Create Journal Entry for the payment
			je = frappe.get_doc({
				"doctype": "Journal Entry",
				"voucher_type": "Journal Entry",
				"posting_date": self.payment_date,
				"company": frappe.defaults.get_user_default("Company"),
				"user_remark": f"Payment from {self.member_name} - {self.description}",
				"accounts": [
					{
						"account": self.get_cash_account(),
						"debit_in_account_currency": self.net_amount,
						"credit_in_account_currency": 0,
						"party_type": "Customer",
						"party": self.get_customer_for_member()
					},
					{
						"account": self.get_income_account(),
						"debit_in_account_currency": 0,
						"credit_in_account_currency": self.net_amount
					}
				]
			})
			
			# Add processing fee entry if applicable
			if self.processing_fee:
				je.accounts.append({
					"account": self.get_expense_account(),
					"debit_in_account_currency": self.processing_fee,
					"credit_in_account_currency": 0
				})
				
				# Adjust the cash account for processing fee
				je.accounts[0]["debit_in_account_currency"] = self.amount
			
			je.insert()
			je.submit()
			
			# Link the journal entry to this payment
			frappe.db.set_value("Dojo Payment", self.name, "journal_entry", je.name)
			
		except Exception as e:
			frappe.log_error(f"Failed to create accounting entry for payment {self.name}: {str(e)}")
	
	def get_cash_account(self):
		"""Get the cash account based on payment method"""
		payment_method_accounts = {
			"Cash": "Cash - Company",
			"Credit Card": "Credit Card Clearing - Company",
			"Debit Card": "Bank - Company",
			"Bank Transfer": "Bank - Company",
			"Check": "Bank - Company",
			"PayPal": "PayPal - Company",
			"Stripe": "Stripe - Company"
		}
		
		return payment_method_accounts.get(self.payment_method, "Cash - Company")
	
	def get_income_account(self):
		"""Get the income account based on payment type"""
		income_accounts = {
			"Monthly Membership": "Membership Income - Company",
			"Annual Membership": "Membership Income - Company",
			"Class Fee": "Class Fee Income - Company",
			"Private Lesson": "Private Lesson Income - Company",
			"Seminar Fee": "Seminar Income - Company",
			"Merchandise": "Merchandise Sales - Company",
			"Registration Fee": "Registration Income - Company",
			"Late Fee": "Late Fee Income - Company"
		}
		
		return income_accounts.get(self.payment_type, "Other Income - Company")
	
	def get_expense_account(self):
		"""Get the expense account for processing fees"""
		return "Payment Processing Fees - Company"
	
	def get_customer_for_member(self):
		"""Get or create customer record for the member"""
		# Check if customer already exists
		customer = frappe.db.get_value("Customer", {"custom_dojo_member": self.member}, "name")
		
		if not customer:
			# Create customer record
			member_doc = frappe.get_doc("Dojo Member", self.member)
			customer_doc = frappe.get_doc({
				"doctype": "Customer",
				"customer_name": member_doc.member_name,
				"customer_type": "Individual",
				"customer_group": "Dojo Members",
				"territory": "All Territories",
				"custom_dojo_member": self.member
			})
			customer_doc.insert()
			customer = customer_doc.name
		
		return customer
	
	def send_payment_receipt(self):
		"""Send payment receipt to member"""
		if self.status != "Completed":
			frappe.throw("Cannot send receipt for incomplete payment")
		
		member_doc = frappe.get_doc("Dojo Member", self.member)
		
		if not member_doc.email:
			frappe.throw("Member email not found")
		
		# Send email with receipt
		frappe.sendmail(
			recipients=[member_doc.email],
			subject=f"Payment Receipt - {self.receipt_number}",
			template="payment_receipt",
			args={
				"member_name": member_doc.member_name,
				"payment": self,
				"dojo_name": frappe.defaults.get_user_default("Company") or "BJJ Dojo"
			},
			attachments=[{
				"fname": f"Receipt-{self.receipt_number}.pdf",
				"fcontent": self.get_receipt_pdf()
			}]
		)
	
	def get_receipt_pdf(self):
		"""Generate PDF receipt"""
		# This would generate a PDF receipt
		# For now, return a placeholder
		return "PDF receipt content would be generated here"


@frappe.whitelist()
def create_membership_payment(member, payment_type, amount, payment_method="Cash"):
	"""Create a membership payment"""
	member_doc = frappe.get_doc("Dojo Member", member)
	
	payment_doc = frappe.get_doc({
		"doctype": "Dojo Payment",
		"member": member,
		"member_name": member_doc.member_name,
		"payment_type": payment_type,
		"amount": amount,
		"payment_date": today(),
		"payment_method": payment_method,
		"description": f"{payment_type} payment for {member_doc.member_name}",
		"status": "Completed"
	})
	
	payment_doc.insert()
	payment_doc.submit()
	
	return payment_doc.name


@frappe.whitelist()
def get_payment_summary(start_date=None, end_date=None):
	"""Get payment summary for dashboard"""
	conditions = []
	params = []
	
	if start_date:
		conditions.append("payment_date >= %s")
		params.append(start_date)
	
	if end_date:
		conditions.append("payment_date <= %s")
		params.append(end_date)
	
	where_clause = "WHERE docstatus = 1 AND status = 'Completed'"
	if conditions:
		where_clause += " AND " + " AND ".join(conditions)
	
	# Total revenue
	total_revenue = frappe.db.sql(f"""
		SELECT IFNULL(SUM(amount), 0) as total
		FROM `tabDojo Payment`
		{where_clause}
	""", params)[0][0] or 0
	
	# Revenue by payment type
	revenue_by_type = frappe.db.sql(f"""
		SELECT payment_type, SUM(amount) as total, COUNT(*) as count
		FROM `tabDojo Payment`
		{where_clause}
		GROUP BY payment_type
		ORDER BY total DESC
	""", params, as_dict=True)
	
	# Revenue by payment method
	revenue_by_method = frappe.db.sql(f"""
		SELECT payment_method, SUM(amount) as total, COUNT(*) as count
		FROM `tabDojo Payment`
		{where_clause}
		GROUP BY payment_method
		ORDER BY total DESC
	""", params, as_dict=True)
	
	# Daily revenue trend
	daily_revenue = frappe.db.sql(f"""
		SELECT payment_date, SUM(amount) as total, COUNT(*) as count
		FROM `tabDojo Payment`
		{where_clause}
		GROUP BY payment_date
		ORDER BY payment_date
	""", params, as_dict=True)
	
	return {
		"total_revenue": total_revenue,
		"revenue_by_type": revenue_by_type,
		"revenue_by_method": revenue_by_method,
		"daily_revenue": daily_revenue
	}


@frappe.whitelist()
def get_member_payment_history(member, limit=50):
	"""Get payment history for a member"""
	return frappe.get_all("Dojo Payment",
		filters={"member": member, "docstatus": 1},
		fields=["name", "payment_type", "amount", "payment_date", "payment_method", 
				"status", "receipt_number", "description"],
		order_by="payment_date desc",
		limit=limit
	)


@frappe.whitelist()
def process_refund(payment_name, refund_amount, reason):
	"""Process a refund for a payment"""
	payment_doc = frappe.get_doc("Dojo Payment", payment_name)
	
	if payment_doc.status != "Completed":
		frappe.throw("Can only refund completed payments")
	
	if flt(refund_amount) > flt(payment_doc.amount):
		frappe.throw("Refund amount cannot exceed original payment amount")
	
	# Create refund payment record
	refund_doc = frappe.get_doc({
		"doctype": "Dojo Payment",
		"member": payment_doc.member,
		"member_name": payment_doc.member_name,
		"payment_type": "Refund",
		"amount": -flt(refund_amount),  # Negative amount for refund
		"payment_date": today(),
		"payment_method": payment_doc.payment_method,
		"description": f"Refund for {payment_doc.name} - {reason}",
		"reference_doctype": "Dojo Payment",
		"reference_name": payment_doc.name,
		"status": "Completed"
	})
	
	refund_doc.insert()
	refund_doc.submit()
	
	# Update original payment status if fully refunded
	if flt(refund_amount) == flt(payment_doc.amount):
		frappe.db.set_value("Dojo Payment", payment_name, "status", "Refunded")
	
	return refund_doc.name