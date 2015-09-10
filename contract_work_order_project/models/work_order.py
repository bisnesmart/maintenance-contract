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


    def _get_stages(self):
        """
        Obtener las etapas del proyecto.
        """
        stages=[]
        stages.extend(
            [
            etapa.id for etapa in self.env['project.task.type'].search(
                [('name', 'in', ['PENDIENTE','SI','NO','REG','BIEN','MAL'])]
            )
            ]
        )

        return stages


    # Función tipo oncreate que genere un project en el que cada línea de
    # la work order sea una tarea. 
    # Si es un producto tipo servicio, es una tarea tal y como lo teníamos pensado
    # Si es un producto tipo 'product', a lo mejor queremos cambiarle el formato, 
    # aunque con la clasificación de sí, no, de momento va que chuta, luego podemos
    # sacar el informe de otra manera sin tocar más 

    # Va a hacer falta meter las líneas en las modificaciones también. 
    @api.model
    def create(self, vals):
        vals_project={}
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].get(
                                            'maintenance.work.order') or '/'
        if 'date' not in vals:
            vals['date'] = time.strftime('%Y-%m-%d')

        # Crear un proyecto.
        #-------------------
        # Obtener valores que pasarle a la creación del proyecto



        vals_project.update(
                {
                    'name': vals.get('name', 'Proyecto '+vals.get('id','pendiente')),
                    'analytic_account_id': vals.get('project_id', False),
                    'active': True,
                    'sequence': 2,
                    # Meter en módulo nuevo:
                    #'members': 
                    'type_ids': [(6,0,self._get_stages())],
                    'use_tasks': True,
                    'use_timesheet': True

                }
            )
        #self.env['project.project'].create(vals_project)

        # Asociar al contrato que en work.order tenemos referenciado por project_id

        # Crear o cargar id de etapas del proyecto.
        # self.env['project.task.type']
        # Crear tareas: De cada línea de la orden de trabajo, sacar una tarea.  
        # self.env['project.task']

        self.env['project.project'].create(vals_project)
        return super(WorkOrder, self).create(vals)
