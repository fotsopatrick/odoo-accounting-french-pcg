# -*- coding: utf-8 -*-
{
    'name': 'Accounting Complete - French PCG',
    'version': '18.0.1.0.1',
    'category': 'Accounting/Accounting',
    'summary': 'Complete accounting solution with French Chart of Accounts (PCG)',
    'description': """
Accounting Complete - Full Accounting for Odoo 18 Community
============================================================

A comprehensive accounting module providing Enterprise-level features for Odoo 18 Community Edition.
Includes the French Chart of Accounts (Plan Comptable General - PCG).

Key Features
------------
* **Chart of Accounts**: Full French PCG with 100+ accounts, 8 account classes
* **Journals**: Sales, Purchases, Bank, Cash, Miscellaneous operations
* **Journal Entries**: Full double-entry accounting with reconciliation
* **Invoicing**: Customer and Supplier invoices with automatic entries
* **Tax Management**: French VAT rates (20%, 10%, 5.5%, 2.1%)
* **Bank Reconciliation**: Match bank statements with payments
* **Analytic Accounting**: Multi-axis cost centers and projects
* **Budgets**: Budget planning and variance analysis
* **Fiscal Years**: Period management and year-end closing
* **Payment Terms**: Flexible payment conditions

Perfect for
-----------
* Small businesses and startups
* Auto-entrepreneurs (French self-employed)
* Accountants managing multiple companies
* Anyone needing accounting without Enterprise license

Chart of Accounts Included
--------------------------
* Class 1: Capital accounts (Capitaux)
* Class 2: Fixed assets (Immobilisations)
* Class 3: Inventory (Stocks)
* Class 4: Third parties - Customers, Suppliers, Tax (Tiers)
* Class 5: Financial accounts - Bank, Cash (Financiers)
* Class 6: Expenses (Charges)
* Class 7: Income (Produits)

Compatible with sale, purchase, and contacts modules.

Support: Create an issue on the app page.
    """,
    'author': 'Code Nomi Nomi',
    'website': 'https://codenominomi.com',
    'license': 'LGPL-3',
    'price': 79.00,
    'currency': 'EUR',
    'support': 'support@codenominomi.com',
    'depends': [
        'base',
        'mail',
        'contacts',
        'sale',
        'purchase',
    ],
    'data': [
        'security/accounting_security.xml',
        'security/ir.model.access.csv',
        'data/account_data.xml',
        'data/account_chart_fr.xml',
        'views/account_account_views.xml',
        'views/account_journal_views.xml',
        'views/account_move_views.xml',
        'views/account_tax_views.xml',
        'views/account_payment_views.xml',
        'views/account_analytic_views.xml',
        'views/account_budget_views.xml',
        'views/account_fiscal_year_views.xml',
        'views/account_reconcile_views.xml',
        'views/account_menu.xml',
    ],
    'images': [
        'static/description/banner.png',
        'static/description/screenshot1.png',
        'static/description/screenshot2.png',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'assets': {},
}
