# Changelog

All notable changes to this module will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [18.0.1.0.1] - 2026-01-07

### Fixed
- Fixed kanban view template rendering for journals
- Journal cards now display correctly with name, code, type, and entry count

## [18.0.1.0.0] - 2026-01-07

### Added
- Initial release for Odoo 18
- Complete French Chart of Accounts (PCG) with 100+ accounts
- All 8 account classes (1-Capitaux to 7-Produits)
- Journal management (Sales, Purchases, Bank, Cash, Miscellaneous)
- Journal entries with double-entry validation
- Customer and supplier invoices
- Payment management and registration
- French VAT taxes (20%, 10%, 5.5%, 2.1%)
- Bank reconciliation features
- Analytic accounting with multi-axis plans
- Budget management and variance analysis
- Fiscal year and period management
- Payment terms configuration
- Fiscal positions for tax mapping
- Security groups (User, Accountant, Manager)
- Full access rights configuration

### Technical
- Compatible with Odoo 18.0 Community Edition
- Uses `<list>` view type (Odoo 18 standard)
- Custom model names with `.custom` suffix to avoid conflicts
- Unique Many2many table names
- Integration with sale, purchase, and contacts modules

## [Unreleased]

### Planned
- OHADA chart of accounts (African standard)
- Additional report templates
- Bank statement import (OFX, CSV)
- Automatic reconciliation improvements
- Multi-currency support enhancements
