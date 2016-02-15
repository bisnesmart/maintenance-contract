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
        ondelete='set null',
        # Esta línea da error al instalar el módulo:
        # default=lambda self: self.env.user.id ,
        )
    # Si es un producto tipo servicio, es una tarea tal y como lo teníamos pensado
    # Si es un producto tipo 'product', a lo mejor queremos cambiarle el formato,
    # aunque con la clasificación de sí, no, de momento va que chuta, luego podemos
    # sacar el informe de otra manera sin tocar más

    # Proyecto asociado a la orden de trabajo.
    project_project_id = fields.Many2one(
                            string="Project",
                            comodel_name='project.project',
                            ondelete='set null',
                            help="Proyecto al que añadir las tareas.\n"
                                "Si no se especifica, se creará uno nuevo.",
                            )


    # @api.model
    @api.multi
    def work_planned(self):
        self.state = 'planned'
        valores = {
            'name': self.name,
            'date': self.date,
            'project_id': self.project_id.id if self.project_id else False,
            'technician_id': self.technician_id.id if self.technician_id else False,


                }
        self.create_project(valores)

    def create_project(self, vals):
        """
        Crear proyecto a partir de los datos de la orden de trabajo.
        @param: vals
            diccionario con los valores relevantes de la orden de trabajo que
            genera el proyecto a crear.
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
        # Contrato asociado al proyecto seleccionado.
        # Donde ahora devolvemos False, podría ir una función _get_contract
        # con la que obtener el valor por defecto del contrato, puede ser útil
        # si se generan tareas a menudo que no correspondan a un contrato.
        # También sería necesario crear _set_contract para establecer el valor
        # por defecto a elección del usuario.
        contract_id = vals.get('project_id', False)
        if contract_id:
            contrato = self.env['account.analytic.account'].search(
                [('id','=',contract_id)]
                )
            # Hemos asociado un contrato, recorreremos el iterable de las
            # líneas de facturación.
            lineas = contrato.recurring_invoice_line_ids
        else:
            # No hemos seleccionado un contrato asociado, creamos las tareas
            # a partir de las líneas de la orden de trabajo:
            # lineas = self.env['maintenance.work.line'].search(
            #     [('id','=',self.line_ids)]
            #     )
            lineas = self.env['maintenance.work.line'].browse(
                self.line_ids
                )

            # lineas = self.env['maintenance.work.line'].search(
            # vals.get('line_ids')

        # El técnico será por defecto el usuario activo.
        values_to_write ={
                            'name': vals.get('name',
                                        'Proyecto '+vals.get('id','pendiente')),
                            'analytic_account_id': contract_id,
                            'active': True,
                            'sequence': 2,
                            'type_ids': [(6,0,self._get_stages())],
                            'use_tasks': True,
                            'use_timesheets': True,
                            #'uid': self.env.user.id,

                        }
        if vals.get('technician_id',False):
            values_to_write['members'] = [(6,0,[vals.get('technician_id')])]
            values_to_write['manager_id'] = vals.get('technician_id')
        vals_project.update(values_to_write)
        vals_task = []
        # Se crea el proyecto asociado a la orden de trabajo, solamente
        # si no se ha seleccionado un proyecto.

        # Proyecto asociado seleccionado:
        related_project = vals.get('project_project_id',False)
        if related_project:
            proyecto = self.env['project.project'].search(
                                        [('id','=',related_project)]
                                        )
        # else:
        #     proyecto = False
        # Si no se ha seleccionado un proyecto en el desplegable, se estaba
        # creando uno, esto funciona bien en la creación mediante formulario,
        # pero en la creación desde el botón de crear trabajos recurrentes
        # genera una excepción ProgrammingError (faltan valores).
        elif vals_project:

            proyecto = self.env['project.project'].create(vals_project)

        # A continuación se generan las tareas a partir de las líneas facturables
        # dentro de la recurrencia del contrato asociado.
        for line in lineas:
            nombre_categoria = line.product_id.categ_id.name or 'Categoria'
            project_category_ids = self.env['project.category'].search(
                [('name','ilike',nombre_categoria)]
                )
            if project_category_ids:
                task_dict = {}
                task_dict['name'] = line.product_id.product_tmpl_id.name or 'Nombre de tarea'
                task_dict['categ_ids'] = [(6,0,[project_cat.id for project_cat in project_category_ids])]
                task_dict['project_id'] = proyecto.id if proyecto else False
                task_dict['stage_id'] = self._get_stages('PENDIENTE')[0]
                vals_task.append(task_dict)
            else:
                vals_task.append(
                {
                # product.product no tiene name
                'name': line.product_id.product_tmpl_id.name or 'Nombre de tarea',
                'project_id': proyecto.id if proyecto else False,
                'stage_id': self._get_stages('PENDIENTE')[0]
                })

        task_ids = []
        for task in vals_task:
            task_ids.append( self.env['project.task'].create(task) )

        # Asignamos valor al campo relacional que nos enlaza la orden de trabajo
        # con el proyecto, pero si no tenemos proyecto (caso en el que la orden
        # se crea desde otra función) tenemos que asignarle mejor el valor.
        self.project_project_id = proyecto.id if proyecto else False

        # TODO: Meter el delivery address en el work order para poder indicar dónde
        # se realiza el trabajo.
