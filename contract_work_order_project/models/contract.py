# -*- coding: utf-8 -*-

from openerp import models, fields, api
from datetime import datetime
import time
from dateutil.relativedelta import relativedelta
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
