
# 📊 Velaris Data Parity Engine

### **Automated Data Quality Validation for Velaris Integrations**

The **Velaris Data Parity Engine** is a Python-based validation framework that analyzes data consistency between **Velaris** and external systems (Salesforce, HubSpot, Stripe, etc.).
It performs **field-level** and **record-level** parity checks, highlights mismatches, and generates detailed output reports automatically.

This project is developed for the **Velaris Data Quality Hackathon 2025**.

---

# 📁 Project Folder Structure

```
velaris-data-parity-engine/
│
├── config/
│   └── (global config files)
│
├── data/
│   ├── bookings/
│   │   ├── SF Custom Object - Bookings to Velaris Custom Object _ DataIQ.csv
│   │   └── SF Custom Object - Bookings to Velaris Custom Object _ DataIQ.xlsx
│   │
│   ├── opportunities/
│   │   └── Salesforce to Velaris Opportunity _ Uberall.xlsx
│   │
│   ├── subscriptions/
│   │   └── Corporate Subscriptions to Velaris _ Salesforce.xlsx
│   │
│   └── mappings/
│       ├── bookings.json
│       ├── opportunities.json
│       └── subscriptions.json
│
├── output/
│   ├── bookings/
│   ├── opportunities/
│   └── subscriptions/
│
├── src/
│   ├── core/
│   │   └── (engine logic)
│   │
│   ├── validators/
│   │   ├── __init__.py
│   │   ├── batch_runner.py
│   │   └── multi_validator.py
│   │
│   └── requirements.txt
│
├── .gitignore
└── pyvenv.cfg
```

---

# 🚀 What This Engine Does

### ✔ Reads input data

From `/data/<object>/...` (Bookings, Opportunities, Subscriptions)

### ✔ Loads validation rules

From `/data/mappings/*.json`
These define:

* Velaris field ↔ Salesforce field mappings
* Data type rules
* Required fields
* Keys for merging

### ✔ Runs parity checks

The validators detect:

* Missing records
* Mismatched values
* Duplicate keys
* Unexpected schema changes
* Fields with null/empty anomalies

### ✔ Saves results

Results are stored in `/output/<object>/...` as:

* mismatch reports
* missing record lists
* summary logs

### ✔ Supports batch or multi-file validation

* `batch_runner.py` → run validator for one dataset
* `multi_validator.py` → validate Bookings, Opportunities, Subscriptions in one go

---

# 🧠 How the System Works

### **1. Load raw data**

From Excel/CSV under `data/<object>/`

### **2. Load mapping**

Used to align Salesforce fields to Velaris fields.

### **3. Merge & Compare**

Record-level join using a configured primary key.

### **4. Identify Issues**

Validator checks:

* Null values
* Type mismatches
* Field mismatches
* Missing Salesforce → Velaris records
* Extra Velaris records

### **5. Output Reports**

Stored under `output/<object>/`

---

# ▶️ Running the Validator

### 1️⃣ Install dependencies

```
pip install -r src/requirements.txt
```

### 2️⃣ Run batch validation

```
python src/validators/batch_runner.py
```

### 3️⃣ Run full (multi-object) validation

```
python src/validators/multi_validator.py
```

---

# ⚙️ Configuration Files

### 📌 Mappings (`data/mappings/*.json`)

Define:

* Column mappings
* Key fields
* Ignore lists
* Tolerance rules

Example:

```json
{
  "primary_key": "Booking ID",
  "mappings": {
    "Velaris Field": "Salesforce Field"
  }
}
```

---

# 📬 Outputs

For each object (bookings, opportunities, subscriptions), the tool generates:

| File                        | Description                              |
| --------------------------- | ---------------------------------------- |
| `mismatches.csv`            | Field-level mismatches                   |
| `missing_in_salesforce.csv` | Exists in Velaris, missing in Salesforce |
| `missing_in_velaris.csv`    | Exists in Salesforce, missing in Velaris |
| `summary.json`              | Quick overview of counts                 |

---

# ☁️ Deployment Notes

You can deploy this on AWS via:

* **Lambda** (for small datasets)
* **EC2** (cron-based execution)
* **ECS/Fargate** (production-ready)
* **S3 input + EventBridge** (serverless scheduled validation)

---

# 👥 Team

**Rumeth**, **Subanya**, **Sandali**
Velaris Data Quality Project

---


