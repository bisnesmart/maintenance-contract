# -*- coding: utf-8 -*-

from openerp import models, fields, api
from datetime import datetime
import time
from dateutil.relativedelta import relativedelta
# Default server date format:  "%Y-%m-%d"
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp.osv import orm
from openerp.tools.translate import _

class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    # Action called by the Close button in contracts:
    @api.multi
    def set_close(self):
        # Compute pending invoiceable lines after last invoice:
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
                        # Para crear la factura automáticamente, se establece
                        # la fecha de próxima factura en hoy, en lugar de la
                        # fecha de fin de contrato:
                        line.recurring_next_date = fields.Date.context_today(self)

        # La fecha se cambia correctamente, pero para que el cron genere la
        # factura, es necesario que el contrato figure como abierto.
        # TODO: Hay que forzar la creación de la factura en este momento.
        self._recurring_create_invoice(self)
        return self.write(
                        {'state': 'close'},
                        context=self.env.context
                        )

    @api.one
    @api.depends('recurring_invoice_line_ids.recurring_last_date')
    def _compute_last_date(self):
        last_date = False
        for line in self.recurring_invoice_line_ids:
            if not last_date or (
                    line.recurring_last_date and
                    line.recurring_last_date > last_date):
                last_date = line.recurring_last_date
        self.computed_last_date = last_date

    # Non-stored field account.analytic.account.computed_next_work_date
    # cannot be searched.
    computed_next_date = fields.Date(
        'Date of Next Invoice',
        compute='_compute_next_date',
        store=True,
        )
    computed_last_date = fields.Date(
        'Date of Last Invoice',
        compute='_compute_last_date',
        store=True
        )

    @api.onchange('date_start')
    def onchange_date_start(self):
        # La función onchange creada en contract_multiple_period hacía que
        # sea cual sea el valor de la fecha de inicio del contrato, al cambiarlo
        # se asigna el mismo valor al campo computed_next_date, sin aplicar
        # ninguna condición.
        pass


class AccountAnalyticInvoiceLine(models.Model):
    _inherit = "account.analytic.invoice.line"


    @api.onchange('periodicity_type')
    def on_change_work_periodicity_type(self):
        """
        Get next and last date for recurring invoices from the parent analytic
        account.
        """
        if not self.recurring_last_date:
            self.recurring_next_date = self.analytic_account_id.computed_next_date
            self.recurring_last_date = self.analytic_account_id.computed_last_date or self.analytic_account_id.date_start
        if self.periodicity_type == 'month':
            self.month_ids = False
        if self.periodicity_type == 'none':
            self.recurring_next_date = False
            self.recurring_last_date = False



    # @api.onchange('periodicity_type')
    # def on_change_periodicity_type(self):
    #     # TODO: Esto puede hacer que se facture en negativo, hay que revisarlo
    #     # recurring_last_date en la línea de factura indica la fecha de creación
    #     # de la última factura.
