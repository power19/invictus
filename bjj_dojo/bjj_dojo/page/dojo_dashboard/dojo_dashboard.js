frappe.pages['dojo_dashboard'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Dojo Dashboard',
		single_column: true
	});

	// Initialize dashboard
	new DojoDashboard(page);
};

class DojoDashboard {
	constructor(page) {
		this.page = page;
		this.setup_dashboard();
		this.load_data();
		this.setup_event_listeners();
	}

	setup_dashboard() {
		// Load the HTML template
		$(frappe.render_template('dojo_dashboard')).appendTo(this.page.body);
		
		// Initialize charts
		this.init_charts();
	}

	init_charts() {
		// Initialize earnings chart
		const earningsCtx = document.getElementById('earnings-chart');
		if (earningsCtx) {
			this.earnings_chart = new Chart(earningsCtx, {
				type: 'line',
				data: {
					labels: [],
					datasets: [{
						label: 'Earnings',
						data: [],
						borderColor: '#007bff',
						backgroundColor: 'rgba(0, 123, 255, 0.1)',
						tension: 0.4,
						fill: true
					}]
				},
				options: {
					responsive: true,
					maintainAspectRatio: false,
					plugins: {
						legend: {
							display: false
						}
					},
					scales: {
						y: {
							beginAtZero: true,
							grid: {
								display: false
							}
						},
						x: {
							grid: {
								display: false
							}
						}
					}
				}
			});
		}

		// Initialize members chart
		const membersCtx = document.getElementById('members-chart');
		if (membersCtx) {
			this.members_chart = new Chart(membersCtx, {
				type: 'line',
				data: {
					labels: [],
					datasets: [{
						label: 'Active Members',
						data: [],
						borderColor: '#28a745',
						backgroundColor: 'rgba(40, 167, 69, 0.1)',
						tension: 0.4,
						fill: true
					}]
				},
				options: {
					responsive: true,
					maintainAspectRatio: false,
					plugins: {
						legend: {
							display: false
						}
					},
					scales: {
						y: {
							beginAtZero: true,
							grid: {
								display: false
							}
						},
						x: {
							grid: {
								display: false
							}
						}
					}
				}
			});
		}
	}

	setup_event_listeners() {
		// Recommended actions toggle
		$(document).on('click', '#recommended-actions', () => {
			$('#recommendations-panel').toggle();
			$('#activity-panel').hide();
		});

		// Recent activity toggle
		$(document).on('click', '#recent-activity', () => {
			$('#activity-panel').toggle();
			$('#recommendations-panel').hide();
		});

		// Period selectors
		$(document).on('change', '#earnings-period', (e) => {
			this.load_earnings_data(e.target.value);
		});

		$(document).on('change', '#members-period', (e) => {
			this.load_members_data(e.target.value);
		});

		// Refresh data every 5 minutes
		setInterval(() => {
			this.load_data();
		}, 300000);
	}

	load_data() {
		this.load_summary_stats();
		this.load_earnings_data('1year');
		this.load_members_data('6months');
		this.load_recommendations();
		this.load_recent_activity();
	}

	load_summary_stats() {
		frappe.call({
			method: 'bjj_dojo.bjj_dojo.doctype.dojo_member.dojo_member.get_members_summary',
			callback: (r) => {
				if (r.message) {
					const data = r.message;
					$('#total-members').text(data.active_members);
					$('#active-members-count').text(data.active_members);
					$('#monthly-revenue').text(frappe.format(data.monthly_revenue, {fieldtype: 'Currency'}));
				}
			}
		});

		// Load classes today count
		frappe.call({
			method: 'bjj_dojo.bjj_dojo.doctype.dojo_class.dojo_class.get_weekly_schedule',
			args: {
				start_date: frappe.datetime.get_today()
			},
			callback: (r) => {
				if (r.message) {
					const today = frappe.datetime.get_today();
					const todayClasses = r.message[today] || [];
					$('#classes-today-count').text(todayClasses.length);
				}
			}
		});

		// Load belt promotions this month
		const startOfMonth = frappe.datetime.month_start();
		frappe.call({
			method: 'frappe.client.get_count',
			args: {
				doctype: 'Belt Promotion',
				filters: {
					promotion_date: ['>=', startOfMonth]
				}
			},
			callback: (r) => {
				if (r.message !== undefined) {
					$('#belt-promotions').text(r.message);
				}
			}
		});
	}

	load_earnings_data(period) {
		let start_date = this.get_period_start_date(period);
		
		frappe.call({
			method: 'bjj_dojo.bjj_dojo.doctype.dojo_payment.dojo_payment.get_payment_summary',
			args: {
				start_date: start_date,
				end_date: frappe.datetime.get_today()
			},
			callback: (r) => {
				if (r.message) {
					const data = r.message;
					$('#total-earnings').text(frappe.format(data.total_revenue, {fieldtype: 'Currency'}));
					
					// Update chart
					if (this.earnings_chart && data.daily_revenue) {
						const labels = data.daily_revenue.map(d => frappe.datetime.str_to_user(d.payment_date));
						const values = data.daily_revenue.map(d => d.total);
						
						this.earnings_chart.data.labels = labels;
						this.earnings_chart.data.datasets[0].data = values;
						this.earnings_chart.update();
					}
				}
			}
		});
	}

	load_members_data(period) {
		// This would load member growth data over time
		// For now, we'll simulate the data
		const labels = this.get_period_labels(period);
		const data = this.generate_member_growth_data(labels.length);
		
		if (this.members_chart) {
			this.members_chart.data.labels = labels;
			this.members_chart.data.datasets[0].data = data;
			this.members_chart.update();
		}
	}

	load_recommendations() {
		// Load recommended actions
		frappe.call({
			method: 'bjj_dojo.api.dashboard.get_recommendations',
			callback: (r) => {
				if (r.message) {
					this.render_recommendations(r.message);
				}
			}
		});
	}

	load_recent_activity() {
		// Load recent member activity
		frappe.call({
			method: 'bjj_dojo.api.dashboard.get_recent_activity',
			callback: (r) => {
				if (r.message) {
					this.render_recent_activity(r.message);
				}
			}
		});
	}

	render_recommendations(recommendations) {
		const container = $('.recommendation-list');
		container.empty();
		
		recommendations.forEach(rec => {
			const item = $(`
				<div class="recommendation-item">
					<div class="recommendation-avatar">
						<img src="${rec.avatar || '/assets/bjj_dojo/images/avatar-placeholder.png'}" alt="Avatar">
					</div>
					<div class="recommendation-content">
						<p><strong>${rec.title}</strong> ${rec.description}</p>
						<button class="btn btn-sm btn-primary" data-action="${rec.action}">View</button>
					</div>
				</div>
			`);
			container.append(item);
		});
	}

	render_recent_activity(activities) {
		const container = $('.activity-list');
		container.empty();
		
		activities.forEach(activity => {
			const item = $(`
				<div class="activity-item">
					<div class="activity-avatar">
						<img src="${activity.avatar || '/assets/bjj_dojo/images/avatar-placeholder.png'}" alt="Avatar">
					</div>
					<div class="activity-content">
						<p><strong>${activity.member_name}</strong> ${activity.description}</p>
						<button class="btn btn-sm btn-primary" data-member="${activity.member}">View</button>
					</div>
				</div>
			`);
			container.append(item);
		});
	}

	get_period_start_date(period) {
		const today = new Date();
		switch(period) {
			case '1month':
				return frappe.datetime.add_months(frappe.datetime.get_today(), -1);
			case '3months':
				return frappe.datetime.add_months(frappe.datetime.get_today(), -3);
			case '6months':
				return frappe.datetime.add_months(frappe.datetime.get_today(), -6);
			case '1year':
			default:
				return frappe.datetime.add_months(frappe.datetime.get_today(), -12);
		}
	}

	get_period_labels(period) {
		const labels = [];
		const today = new Date();
		let months = 6;
		
		switch(period) {
			case '1month':
				months = 1;
				break;
			case '3months':
				months = 3;
				break;
			case '6months':
				months = 6;
				break;
		}
		
		for (let i = months; i >= 0; i--) {
			const date = new Date(today.getFullYear(), today.getMonth() - i, 1);
			labels.push(date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' }));
		}
		
		return labels;
	}

	generate_member_growth_data(length) {
		// Generate sample member growth data
		const data = [];
		let baseValue = 450;
		
		for (let i = 0; i < length; i++) {
			baseValue += Math.floor(Math.random() * 20) - 5; // Random growth/decline
			data.push(Math.max(baseValue, 400)); // Minimum 400 members
		}
		
		return data;
	}
}

// Include Chart.js if not already loaded
if (typeof Chart === 'undefined') {
	frappe.require('/assets/frappe/js/lib/chart.min.js');
}