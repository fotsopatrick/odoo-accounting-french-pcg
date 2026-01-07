====================================
Accounting Complete - French PCG
====================================

.. image:: https://img.shields.io/badge/license-LGPL--3-blue.svg
   :target: https://www.gnu.org/licenses/lgpl-3.0.html
   :alt: License: LGPL-3

.. image:: https://img.shields.io/badge/Odoo-18.0-brightgreen.svg
   :alt: Odoo Version

A comprehensive accounting module for Odoo 18 Community Edition that provides
Enterprise-level features. Includes the complete French Chart of Accounts
(Plan Comptable General - PCG).

Features
========

Chart of Accounts
-----------------
* Complete French PCG with 100+ pre-configured accounts
* All 8 account classes (Capitaux, Immobilisations, Stocks, Tiers, Financiers, Charges, Produits)
* Hierarchical account structure
* Account tags for custom classification

Journals
--------
* Pre-configured journals: Sales (VTE), Purchases (ACH), Bank (BNK), Cash (CAI)
* Miscellaneous operations journal (OD)
* Opening entries journal (AN)
* Automatic sequence numbering

Journal Entries
---------------
* Full double-entry accounting
* Balance validation (debit = credit)
* Draft, Posted, and Cancelled states
* Automatic entries from invoices

Invoicing
---------
* Customer invoices (Factures clients)
* Supplier invoices (Factures fournisseurs)
* Credit notes (Avoirs)
* Automatic accounting entries generation

Tax Management
--------------
* French VAT rates: 20%, 10%, 5.5%, 2.1%
* Separate purchase and sale taxes
* Tax-inclusive and tax-exclusive pricing
* Automatic tax calculation

Bank Reconciliation
-------------------
* Bank statement import
* Manual reconciliation
* Automatic matching rules
* Statement validation

Analytic Accounting
-------------------
* Multi-axis analytic plans
* Cost centers
* Project accounting
* Analytic distribution

Budgets
-------
* Budget planning by account
* Multiple budget versions
* Variance analysis
* Budget vs actual comparison

Fiscal Periods
--------------
* Fiscal year management
* Monthly/quarterly periods
* Period closing
* Year-end operations

Installation
============

1. Copy the ``accounting_custom`` folder to your Odoo addons directory
2. Update the apps list in Odoo
3. Install the module from Apps menu
4. The French PCG chart of accounts will be automatically loaded

Configuration
=============

After installation:

1. Go to **Accounting > Configuration > Chart of Accounts** to view accounts
2. Go to **Accounting > Configuration > Journals** to configure journals
3. Go to **Accounting > Configuration > Taxes** to adjust tax rates
4. Create a new **Fiscal Year** before recording transactions

Usage
=====

Creating a Customer Invoice
---------------------------
1. Go to **Accounting > Customers > Invoices**
2. Click **Create**
3. Select a customer (or create new)
4. Add invoice lines with products/services
5. Click **Confirm** to validate

Recording a Payment
-------------------
1. On a validated invoice, click **Register Payment**
2. Select the payment journal (Bank/Cash)
3. Enter the payment amount
4. Validate the payment

Creating a Journal Entry
------------------------
1. Go to **Accounting > Accounting > Journal Entries**
2. Click **Create**
3. Add balanced lines (debit = credit)
4. Click **Post** to validate

Account Codes Reference
=======================

==================  ========================  ================
Code                Name                      Type
==================  ========================  ================
401000              Fournisseurs              Payable
411000              Clients                   Receivable
512000              Banques                   Bank
530000              Caisse                    Cash
445700              TVA collectee             Tax
445660              TVA deductible sur ABS    Tax
607000              Achats de marchandises    Expense
707000              Ventes de marchandises    Income
706000              Prestations de services   Income
==================  ========================  ================

Bug Tracker
===========

Bugs are tracked on the app page. In case of trouble, please check there
if your issue has already been reported.

Credits
=======

Authors
-------
* Code Nomi Nomi

Contributors
------------
* Development Team

Maintainers
-----------
This module is maintained by Code Nomi Nomi.

License
=======

This module is licensed under LGPL-3.

.. image:: https://www.gnu.org/graphics/lgplv3-147x51.png
   :target: https://www.gnu.org/licenses/lgpl-3.0.html
