# Heritage Foods - Module Testing Checklist

## Prerequisites

### 1. Configuration File Setup
- [ ] Add `addons_custom` to `odoo.conf`:
  ```ini
  addons_path = /path/to/odoo/addons,/path/to/odoo/addons_custom
  ```
- [ ] Restart Odoo server
- [ ] Go to Apps → Update Apps List

### 2. Core Modules Installation (Required First)
- [ ] Install **Inventory** module (`stock`)
- [ ] Install **Sales** module (`sale`)
- [ ] Install **Point of Sale** module (`point_of_sale`)
- [ ] Install **Product Expiry** module (`product_expiry`)
- [ ] Install **eCommerce** module (`website_sale`) - Note: This will also install Website module

### 3. Enable Required Settings
Navigate to: **Inventory → Configuration → Settings**
- [ ] Enable **Storage Locations**
- [ ] Enable **Multi-Step Routes**
- [ ] Enable **Lots & Serial Numbers**
- [ ] Enable **Expiration Dates**

---

## Module 1: stock_modifier

### Installation
- [ ] Module appears in Apps list (search: "Heritage Foods - Stock Modifier")
- [ ] Install the module successfully (no errors)
- [ ] Check module dependencies: `stock`, `product_expiry`

### Warehouse Verification
Navigate to: **Inventory → Configuration → Warehouses**

#### Lagos HQ Warehouse
- [ ] Warehouse exists with name: **Lagos HQ**
- [ ] Warehouse code: **LHQ**
- [ ] Reception steps: One step (receipt)
- [ ] Delivery steps: Ship only

#### Abuja Warehouse
- [ ] Warehouse exists with name: **Abuja**
- [ ] Warehouse code: **ABJ**
- [ ] Reception steps: One step (receipt)
- [ ] Delivery steps: Ship only

### Stock Locations Verification
Navigate to: **Inventory → Configuration → Locations**

#### Lagos HQ - Stock Sub-locations
Under **Lagos HQ/Stock**, verify these locations exist:
- [ ] **G-Flakes (Finished Goods)**
- [ ] **G-Flakes (Empty Packs)**
- [ ] **Ingredients (Garri, Sugar, Powdered Milk, Peanuts)**

#### Lagos HQ - Sales Channel Locations
Under **Lagos HQ** (view location), verify:
- [ ] **Traffic Hawkers (FOTS Team)**
- [ ] **Field Sales Agents**
- [ ] **Student Ambassadors**
- [ ] **Returns**
- [ ] **Direct-to-Consumer (Web)** (should be a view/parent location)
  - [ ] **Direct - Channel 1** (under D2C Web)
  - [ ] **Direct - Channel 2** (under D2C Web)
- [ ] **Scrap** (usage type: Inventory, scrap location: Yes)

#### Abuja - Stock Sub-locations
Under **Abuja/Stock**, verify these locations exist:
- [ ] **G-Flakes (Finished Goods)**
- [ ] **G-Flakes (Empty Packs)**
- [ ] **Ingredients (Garri, Sugar, Powdered Milk, Peanuts)**

#### Abuja - Sales Channel Locations
Under **Abuja** (view location), verify:
- [ ] **Traffic Hawkers (FOTS Team)**
- [ ] **Field Sales Agents**
- [ ] **Student Ambassadors**
- [ ] **Returns**
- [ ] **Direct-to-Consumer (Web)** (should be a view/parent location)
  - [ ] **Direct - Channel 1** (under D2C Web)
  - [ ] **Direct - Channel 2** (under D2C Web)
- [ ] **Scrap** (usage type: Inventory, scrap location: Yes)

### Reordering Rules (Manual Setup Required)
**Note:** Reordering rules are NOT auto-created. Create manually after products exist.

Navigate to: **Inventory → Configuration → Reordering Rules**

For **G-Flakes** product (create product first):
- [ ] Create reordering rule for Lagos HQ
  - Product: G-Flakes
  - Location: Lagos HQ/Stock/G-Flakes (Finished Goods)
  - Min Quantity: **720** (30% of 2,400)
  - Max Quantity: **2,400**
  - Trigger: Auto
- [ ] Create reordering rule for Abuja (optional)
  - Product: G-Flakes
  - Location: Abuja/Stock/G-Flakes (Finished Goods)
  - Min Quantity: **720**
  - Max Quantity: **2,400**
  - Trigger: Auto

### Testing
- [ ] Try creating a stock move between locations
- [ ] Verify location hierarchy displays correctly
- [ ] Check that scrap locations are marked as scrap type

---

## Module 2: sales_modifier

### Installation
- [ ] Module appears in Apps list (search: "Heritage Foods - Sales Modifier")
- [ ] Install the module successfully (no errors)
- [ ] Check module dependencies: `sale`, `sales_team`

### Sales Teams Verification
Navigate to: **Sales → Configuration → Sales Teams**

- [ ] **Field Sales Agents** team exists
  - Sequence: 10
  - Active: Yes
- [ ] **Student Ambassadors** team exists
  - Sequence: 20
  - Active: Yes

### Access Restrictions Testing

#### Setup Test Users
Create test users: **Settings → Users & Companies → Users**

1. **Test Salesperson 1**
   - [ ] Create user (e.g., "Agent John")
   - [ ] Access Rights: Sales / User: Own Documents Only
   - [ ] Assign to sales team: Field Sales Agents

2. **Test Salesperson 2**
   - [ ] Create user (e.g., "Ambassador Mary")
   - [ ] Access Rights: Sales / User: Own Documents Only
   - [ ] Assign to sales team: Student Ambassadors

3. **Test Sales Manager**
   - [ ] Create user (e.g., "Manager Admin")
   - [ ] Access Rights: Sales / Administrator

#### Test Customer Access Restrictions
- [ ] Login as **Test Salesperson 1**
  - [ ] Create a customer (assign to self)
  - [ ] Verify: Can only see own customers
  - [ ] Verify: Cannot see customers created by Salesperson 2
  - [ ] Logout

- [ ] Login as **Test Salesperson 2**
  - [ ] Create a customer (assign to self)
  - [ ] Verify: Can only see own customers
  - [ ] Verify: Cannot see customers created by Salesperson 1
  - [ ] Logout

- [ ] Login as **Test Sales Manager**
  - [ ] Verify: Can see ALL customers (from both salespersons)

#### Test Sales Order Access Restrictions
- [ ] Login as **Test Salesperson 1**
  - [ ] Create a sales order (for own customer)
  - [ ] Verify: Can only see own sales orders
  - [ ] Verify: Cannot see sales orders created by Salesperson 2
  - [ ] Logout

- [ ] Login as **Test Salesperson 2**
  - [ ] Create a sales order (for own customer)
  - [ ] Verify: Can only see own sales orders
  - [ ] Verify: Cannot see sales orders created by Salesperson 1
  - [ ] Logout

- [ ] Login as **Test Sales Manager**
  - [ ] Verify: Can see ALL sales orders (from both salespersons)

### Security Rules Verification
Navigate to: **Settings → Technical → Security → Record Rules**

Search for rules from `sales_modifier`:
- [ ] **Personal Sales Orders Only** rule exists
  - Model: sale.order
  - Domain: [('user_id', '=', user.id)]
  - Groups: Sales / User: Own Documents Only
  - Permissions: Read, Write, Create (NOT Unlink)

- [ ] **Personal Customers Only** rule exists
  - Model: res.partner
  - Domain: [('user_id', '=', user.id)]
  - Groups: Sales / User: Own Documents Only
  - Permissions: Read, Write, Create (NOT Unlink)

---

## Module 3: point_of_sale_modifier

### Installation
- [ ] Module appears in Apps list (search: "Heritage Foods - Point of Sale Modifier")
- [ ] Install the module successfully (no errors)
- [ ] Check module dependencies: `point_of_sale`, `stock_modifier`

### POS Configuration (Manual Setup Required)
**Note:** POS config is NOT auto-created. Create manually via UI.

Navigate to: **Point of Sale → Configuration → Point of Sale**

#### Create POS for Traffic Hawkers
- [ ] Click **Create**
- [ ] Name: **Traffic Hawkers (FOTS Team)**
- [ ] Warehouse: **Lagos HQ**
- [ ] Default Location: **Lagos HQ/Traffic Hawkers (FOTS Team)**
- [ ] Enable: **Improve navigation for imprecise industrial touchscreens** (for mobile)
- [ ] Configure payment methods (Cash, Mobile Money, etc.)
- [ ] Save configuration

#### Create POS Users
Navigate to: **Settings → Users & Companies → Users**

For each Traffic Hawker:
- [ ] Create user (e.g., "Hawker Ayo")
- [ ] Access Rights: Point of Sale / User
- [ ] Allowed POS: Traffic Hawkers (FOTS Team)
- [ ] Default warehouse: Lagos HQ

#### Test POS Session
- [ ] Login as POS user
- [ ] Open POS session
- [ ] Verify: Can access POS interface
- [ ] Verify: Mobile-friendly interface enabled
- [ ] Verify: Correct warehouse and location
- [ ] Create test order
- [ ] Process payment
- [ ] Close session
- [ ] Verify: Stock moved from correct location

### Additional POS Settings to Configure
- [ ] Product categories for quick access
- [ ] Pricelists (if needed)
- [ ] Receipt format
- [ ] Customer display settings (if applicable)

---

## Module 4: auto_database_backup (Modified)

### Verify Module Still Works
- [ ] Module is installed (should already be installed)
- [ ] No errors on Odoo startup related to missing dependencies

### Test Local Backup (No External Dependencies)
Navigate to: **Settings → Technical → Database Backup**

- [ ] Create new backup configuration
- [ ] Name: **Test Local Backup**
- [ ] Database Name: [your database name]
- [ ] Master Password: [your master password]
- [ ] Backup Format: Zip
- [ ] Backup Destination: **Local Storage**
- [ ] Backup Path: [valid local path, e.g., `/tmp/odoo_backups`]
- [ ] Backup Frequency: Daily
- [ ] Save
- [ ] Verify: No errors about missing Python libraries
- [ ] Test connection (if available)
- [ ] Verify: Backup created successfully

### Test FTP Backup (No External Dependencies)
- [ ] Create new backup configuration
- [ ] Backup Destination: **FTP**
- [ ] Configure FTP settings (host, port, user, password, path)
- [ ] Test connection
- [ ] Verify: No errors about missing Python libraries
- [ ] Verify: Can connect to FTP server

### Test External Backup Options (Should Show Helpful Errors)

#### Dropbox (Requires 'dropbox' library)
- [ ] Create new backup configuration
- [ ] Backup Destination: **Dropbox**
- [ ] Try to get authorization code
- [ ] Verify: Shows error message: "Please install 'dropbox' Python library to use Dropbox backup."
- [ ] Error message is clear and helpful

#### Amazon S3 (Requires 'boto3' library)
- [ ] Create new backup configuration
- [ ] Backup Destination: **Amazon S3**
- [ ] Try to test connection
- [ ] Verify: Shows error message: "Please install 'boto3' Python library to use Amazon S3 backup."
- [ ] Error message is clear and helpful

#### SFTP (Requires 'paramiko' library)
- [ ] Create new backup configuration
- [ ] Backup Destination: **SFTP**
- [ ] Try to test connection
- [ ] Verify: Shows error message: "Please install 'paramiko' Python library to use SFTP backup."
- [ ] Error message is clear and helpful

#### NextCloud (Requires 'nextcloud-api-wrapper' and 'pyncclient' libraries)
- [ ] Create new backup configuration
- [ ] Backup Destination: **Next Cloud**
- [ ] Try to test connection
- [ ] Verify: Shows error message: "Please install 'nextcloud-api-wrapper' and 'pyncclient' Python libraries to use NextCloud backup."
- [ ] Error message is clear and helpful

### Optional: Test with Libraries Installed
If you want to test external backup destinations:

1. **Install required library** (example for Dropbox):
   ```bash
   pip3 install dropbox
   ```

2. **Restart Odoo**

3. **Test Dropbox backup**:
   - [ ] Create backup configuration
   - [ ] Get authorization code (should work now)
   - [ ] Complete OAuth flow
   - [ ] Test backup creation
   - [ ] Verify: Backup uploaded to Dropbox

Repeat for other destinations as needed.

---

## Integration Testing

### End-to-End Workflow Test

#### Scenario: Field Sales Agent Creates Order
1. **Setup**
   - [ ] Create product: G-Flakes (storable, tracked by lots)
   - [ ] Add initial stock to Lagos HQ/Stock/G-Flakes (Finished Goods)
   - [ ] Create Field Sales Agent user

2. **Sales Order Flow**
   - [ ] Login as Field Sales Agent
   - [ ] Create customer (assign to self)
   - [ ] Create sales order for G-Flakes
   - [ ] Confirm order
   - [ ] Verify: Delivery order created
   - [ ] Verify: Stock reserved from correct location

3. **Delivery**
   - [ ] Process delivery
   - [ ] Verify: Stock moved from Lagos HQ/Stock to Field Sales Agents location
   - [ ] Verify: Lot/Serial number tracked

#### Scenario: POS Sale by Traffic Hawker
1. **Setup**
   - [ ] Create POS user (Traffic Hawker)
   - [ ] Ensure stock in Traffic Hawkers location

2. **POS Sale**
   - [ ] Login as POS user
   - [ ] Open POS session
   - [ ] Create sale for G-Flakes
   - [ ] Process payment
   - [ ] Close session
   - [ ] Verify: Stock deducted from Traffic Hawkers location
   - [ ] Verify: Sale recorded correctly

#### Scenario: Reordering Rule Triggers
1. **Setup**
   - [ ] Ensure reordering rule is active for G-Flakes
   - [ ] Current stock: Above minimum (e.g., 1000 units)

2. **Trigger Reorder**
   - [ ] Create sales orders to reduce stock below 720 units
   - [ ] Run scheduler: Inventory → Operations → Run Scheduler
   - [ ] Verify: Purchase quotation or manufacturing order created
   - [ ] Verify: Quantity to order brings stock to 2,400 units

---

## Common Issues & Troubleshooting

### Module Installation Issues
- **Issue**: Module not appearing in Apps list
  - [ ] Check `addons_path` in `odoo.conf`
  - [ ] Restart Odoo server
  - [ ] Update Apps List

- **Issue**: Dependency errors
  - [ ] Ensure core modules installed first (stock, sale, point_of_sale)
  - [ ] Check module dependencies in `__manifest__.py`

### Location Issues
- **Issue**: Locations not created
  - [ ] Check warehouse was created first
  - [ ] Check XML data loaded (no errors in log)
  - [ ] Verify `noupdate="1"` in XML files

- **Issue**: Cannot find specific location
  - [ ] Check location hierarchy (parent/child relationships)
  - [ ] Verify location usage type (internal, view, inventory)

### Access Restriction Issues
- **Issue**: Salesperson can see all records
  - [ ] Check user has correct access rights (Sales / User: Own Documents Only)
  - [ ] Verify record rules are active
  - [ ] Check user is assigned to correct sales team

- **Issue**: Sales Manager cannot see all records
  - [ ] Check user has Sales / Administrator rights
  - [ ] Record rules should NOT apply to managers

### Backup Issues
- **Issue**: Local backup fails
  - [ ] Check backup path exists and is writable
  - [ ] Verify master password is correct
  - [ ] Check disk space

- **Issue**: External backup shows dependency error
  - [ ] This is expected behavior
  - [ ] Install required Python library if you want to use that destination
  - [ ] Restart Odoo after installing library

---

## Sign-Off

### Module: stock_modifier
- Tested by: ________________
- Date: ________________
- Status: ☐ Pass ☐ Fail
- Notes: ________________________________

### Module: sales_modifier
- Tested by: ________________
- Date: ________________
- Status: ☐ Pass ☐ Fail
- Notes: ________________________________

### Module: point_of_sale_modifier
- Tested by: ________________
- Date: ________________
- Status: ☐ Pass ☐ Fail
- Notes: ________________________________

### Module: auto_database_backup
- Tested by: ________________
- Date: ________________
- Status: ☐ Pass ☐ Fail
- Notes: ________________________________

---

## Additional Notes

**Important Reminders:**
1. Always test in a **development/staging environment** first
2. Create database backup before installing modules
3. Document any issues or deviations from expected behavior
4. Take screenshots of successful tests for documentation
5. Report any errors with full error messages and logs

**Contact for Issues:**
- Module Developer: [Your contact info]
- Project Manager: [PM contact info]
