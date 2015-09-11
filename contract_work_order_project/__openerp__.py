# -*- coding: utf-8 -*-
{
    'name': 'Create Project from Work Orders',
    'version': '0.1',
    'author': 'bisneSmart',
    'summary': "Create a project from a work order when this is saved.",
    'website': 'http://www.bisneSmart.com',
    'description':
    """
    When a Work Order is created, generate a project where every line of the
    work order is a task. 

    This module depends on Domatix's set of modules around contract modifications.
    """,
    'images': [],
    'depends': [
            'contract_work_order',
            'report_project_task',
                ],
    'category': 'Project Management',
    'data': [
        #'data/task_data.xml',
        'views/work_order_project_view.xml',
        
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
