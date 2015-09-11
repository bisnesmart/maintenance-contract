# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, fields, api
import time


class WorkOrder(models.Model):
    """ Maintenance Work Order link to project. """
    _inherit = 'maintenance.work.order'


    def _get_stages(self,names=False):
        """
        Obtener las etapas del proyecto.
        """
        stages=[]
        if type(names) is str:
            names = [names]
        elif not names:
            names = ['PENDIENTE','SI','NO','REG','BIEN','MAL']
        stages.extend(
            [
            etapa.id for etapa in self.env['project.task.type'].search(
                [('name', 'in', names)]
            )
            ]
        )

        return stages


    technician_id = fields.Many2one(
        string='Técnico asignado',
        comodel_name='res.users',
        ondelete='set null')
    # Si es un producto tipo servicio, es una tarea tal y como lo teníamos pensado
    # Si es un producto tipo 'product', a lo mejor queremos cambiarle el formato, 
    # aunque con la clasificación de sí, no, de momento va que chuta, luego podemos
    # sacar el informe de otra manera sin tocar más 

    # Proyecto asociado a la orden de trabajo. 
    project_project_id = fields.Many2one(string="Project",
        comodel_name='project.project',ondelete='set null')

 
    @api.model
    def create(self, vals):
        """
        Crea un proyecto a partir de los datos de la orden de trabajo
        """
        vals_project={}
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].get(
                                            'maintenance.work.order') or '/'
        if 'date' not in vals:
            vals['date'] = time.strftime('%Y-%m-%d')

        # Crear un proyecto.
        #-------------------
        # Obtener valores que pasarle a la creación del proyecto

        contract_id = vals.get('project_id', False)
        if contract_id:
            contrato = self.env['account.analytic.account'].search(
                [('id','=',contract_id)]
                )
        technician_id = contrato.manager_id.id


        vals_project.update(
                {
                    'name': vals.get('name', 'Proyecto '+vals.get('id','pendiente')),
                    'analytic_account_id': contract_id,
                    'active': True,
                    'sequence': 2, 
                    'type_ids': [(6,0,self._get_stages())],
                    'use_tasks': True,
                    'use_timesheets': True,
                    'manager_id': technician_id,
                    'members': [(6,0,[technician_id])],

                }
            )
        vals_task = []
        proyecto = self.env['project.project'].create(vals_project)

        for line in contrato.recurring_invoice_line_ids:
            nombre_categoria = line.product_id.categ_id.name or 'Categoria'
            project_category_ids = self.env['project.category'].search(
                [('name','ilike',nombre_categoria)]
                ) 
            if project_category_ids:
                vals_task.append(
                {
                # product.product no tiene name
                'name': line.product_id.product_tmpl_id.name or 'Nombre de tarea',
                'categ_ids': [(6,0,[project_cat.id for project_cat in project_category_ids])],
                'project_id': proyecto.id,
                'stage_id': self._get_stages('PENDIENTE')[0]
                }
                )
            else:
                vals_task.append(
                {
                # product.product no tiene name
                'name': line.product_id.product_tmpl_id.name or 'Nombre de tarea',
                'project_id': proyecto.id,
                'stage_id': self._get_stages('PENDIENTE')[0]
                })

        task_ids = []
        for task in vals_task:
            task_ids.append( self.env['project.task'].create(task) )

        vals.update(
                {
                    'project_project_id': proyecto.id,
                    'technician_id': technician_id
                }
            )
            
        return super(WorkOrder, self).create(vals)


        # Meter el delivery address en el work order para poder indicar dónde
        # se realiza el trabajo. 



