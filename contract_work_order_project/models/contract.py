# -*- coding: utf-8 -*-

from openerp import models, fields, api
from datetime import datetime
import time
from dateutil.relativedelta import relativedelta
# Default server date format:  "%Y-%m-%d"
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp.osv import orm
from openerp.tools.translate import _

WORK_PERIODICITY_TYPE = [
    ('none', 'None'),
    ('unique', 'Unique'),
    ('recursive', 'Recursive'),
    ('month', 'Specified Months'),]


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'
    technician_id = fields.Many2many()

    # Action called by the Close button in contracts:
    @api.multi
    def set_close(self):
        # Compute pending invoiceable lines after last invoice:
        #date_format = '%Y-%m-%d'
        # Date of the next invoice line (invoice or work).
        # It's a string (!):
        invoice_date = self.computed_next_date
        if self.date:
            ending_date = datetime.strptime(self.date,
                                            DEFAULT_SERVER_DATE_FORMAT)
        else:
            # ending_date is a datetime object
            ending_date = datetime.today()
            self.date = fields.Date.context_today(self)
        if self.recurring_invoices:
            for line in self.recurring_invoice_line_ids:
                # Si la línea tiene como fecha de factura la fecha que corresponde
                # a la siguiente factura, seguimos procesando la línea:
                if line.recurring_next_date == invoice_date:
                    # Si la unidad de medida para facturación son días y la
                    # facturación de la línea es mensual:
                    if 'Day' in line.uom_id.name and \
                      line.periodicity_type == 'recursive' and \
                      line.recurring_rule_type == 'monthly':
                        # calculamos los días transcurridos desde la última factura:
                        if line.recurring_last_date:
                            line.quantity = int((ending_date - datetime.strptime(
                                line.recurring_last_date,
                                DEFAULT_SERVER_DATE_FORMAT)).days)
                        else:
                            line.quantity = int(
                                (ending_date - datetime.today()).days
                            )
                        line.recurring_next_date = self.date
        return self.write(
                        {'state': 'close'},
                        context=self.env.context
                        )

class AccountAnalyticInvoiceLine(models.Model):
    _inherit = "account.analytic.invoice.line"

    @api.onchange('product_id')
    def on_change_productid_update(self):
        self.price_unit = self.product_id.lst_price
        self.work_description = self.product_id.work_description
        self.name = self.product_id.name
        self.uom_id = self.product_id.uom_id

    @api.onchange('periodicity_type')
    def invoicebale_false(self):
        if self.periodicity_type != "none":
            self.work_to_invoice = False

    @api.onchange('periodicity_type')
    def on_change_work_periodici_type(self):
        if not self.recurring_last_work_date:
            self.recurring_next_work_date = self.analytic_account_id.date_start
        if self.work_periodicity_type == 'months':
            self.work_month_ids = False

    @api.onchange('periodicity_type')
    def on_change_periodicity_type(self):
        # TODO: Esto puede hacer que se facture en negativo, hay que revisarlo
        if not self.recurring_last_date:
            self.recurring_last_date = self.analytic_account_id.date_start

    @api.onchange('month_ids')
    def on_change_work_month_ids(self):
        date = self.recurring_last_work_date or self.analytic_account_id.date_start
        time = datetime.strptime(date, DEFAULT_SERVER_DATE_FORMAT)
        time = self.get_date_by_month(time, self.work_month_ids, next=False)
        date = datetime.strftime(time, DEFAULT_SERVER_DATE_FORMAT)
        self.recurring_next_work_date = date

    @api.one
    def set_next_work_period_date(self):
        date = self.recurring_next_work_date
        self.recurring_last_work_date = date
        time = datetime.strptime(date, DEFAULT_SERVER_DATE_FORMAT)
        if self.work_periodicity_type == 'none':
            time = False
        elif self.work_periodicity_type == 'recursive':
            if self.work_recurring_rule_type == 'daily':
                time = time+relativedelta(days=+self.work_recurring_interval)
            elif self.work_recurring_rule_type == 'weekly':
                time = time+relativedelta(weeks=+self.work_recurring_interval)
            elif self.work_recurring_rule_type == 'monthly':
                time = time+relativedelta(months=+self.work_recurring_interval)
        elif self.work_periodicity_type == 'month' and len(self.work_month_ids) > 0:
            time = self.get_date_by_month(time, self.work_month_ids, next=True)
        next_date = time and datetime.strftime(
            time, DEFAULT_SERVER_DATE_FORMAT)
        self.recurring_next_work_date = next_date

    work_periodicity_type = fields.Selection(
        WORK_PERIODICITY_TYPE,
        default='none',
        string='Work Periodicity Type')
    work_recurring_rule_type = fields.Selection(
        [('daily', 'Day(s)'),
        ('weekly', 'Week(s)'),
        ('monthly', 'Month(s)'),
        ('yearly', 'Year(s)')],
        string='Work Recurrency',
        help="Work order automatically repeat at specified interval")
    work_recurring_interval = fields.Integer(
        string='Repeat Every',
        help="Repeat every (Days/Week/Month/Year)")
    work_month_ids = fields.Many2many(
        'contract.month',
        string='Months')
    recurring_next_work_date = fields.Date(
        string='Date To Work',
        default=datetime.now())
    recurring_last_work_date = fields.Date(
        string='Date Last Work',
        default=datetime.now())
    work_description = fields.Html(
        string='Work Description')
    work_to_invoice = fields.Boolean(
        string='Invoiceable',
        default=False)


    @api.one
    def _prepare_work_line_data(self):
        values = {
            'product_id': self.product_id.id,
            'product_uom_qty': self.quantity,
            'product_uom_id': self.uom_id.id,
            'contract_line_id': self.id,
            'work_description': self.work_description,
            'to_invoice': self.work_to_invoice
        }
        return values
