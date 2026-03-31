"""
One-time setup: creates SQLite database with synthetic customer data.
Run: python setup_data.py
"""
import sqlite3
import os
import sys

# Ensure config path is accessible
sys.path.insert(0, os.path.dirname(__file__))
from config import DB_PATH


def create_database():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.executescript("""
        DROP TABLE IF EXISTS support_tickets;
        DROP TABLE IF EXISTS customers;

        CREATE TABLE customers (
            id          INTEGER PRIMARY KEY,
            name        TEXT    NOT NULL,
            email       TEXT    UNIQUE,
            phone       TEXT,
            plan        TEXT,
            join_date   TEXT,
            status      TEXT,
            address     TEXT,
            total_spend REAL
        );

        CREATE TABLE support_tickets (
            id          INTEGER PRIMARY KEY,
            customer_id INTEGER,
            date        TEXT,
            category    TEXT,
            issue       TEXT,
            status      TEXT,
            priority    TEXT,
            resolution  TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        );
    """)

    customers = [
        (1,  "Ema Johnson",     "ema.johnson@email.com",    "555-1234", "Premium",    "2022-03-15", "Active",   "123 Main St, NY", 2450.00),
        (2,  "Robert Chen",     "robert.chen@email.com",    "555-2345", "Basic",      "2023-01-10", "Active",   "456 Oak Ave, CA", 890.50),
        (3,  "Alice Brown",     "alice.brown@email.com",    "555-3456", "Premium",    "2021-11-20", "Inactive", "789 Pine Rd, TX", 5200.75),
        (4,  "Michael Davis",   "michael.davis@email.com",  "555-4567", "Enterprise", "2020-06-05", "Active",   "321 Elm St, FL",  12000.00),
        (5,  "Sarah Wilson",    "sarah.wilson@email.com",   "555-5678", "Basic",      "2023-08-22", "Active",   "654 Maple Dr, WA", 345.25),
        (6,  "James Martinez",  "james.martinez@email.com", "555-6789", "Premium",    "2022-12-01", "Active",   "987 Cedar Ln, IL", 3750.00),
        (7,  "Emily Taylor",    "emily.taylor@email.com",   "555-7890", "Enterprise", "2019-04-15", "Active",   "147 Birch Blvd, MA", 18500.00),
        (8,  "David Anderson",  "david.anderson@email.com", "555-8901", "Basic",      "2024-01-05", "Active",   "258 Walnut Way, CO", 125.00),
        (9,  "Lisa Thomas",     "lisa.thomas@email.com",    "555-9012", "Premium",    "2021-07-30", "Inactive", "369 Spruce St, OR", 4100.50),
        (10, "Kevin Jackson",   "kevin.jackson@email.com",  "555-0123", "Basic",      "2023-05-18", "Active",   "741 Ash Ave, NV", 670.25),
    ]

    cursor.executemany(
        "INSERT INTO customers VALUES (?,?,?,?,?,?,?,?,?)",
        customers
    )

    tickets = [
        # Ema Johnson (1)
        (1,  1, "2023-05-10", "Billing",   "Duplicate charge on monthly subscription",    "Resolved",    "High",   "Refund issued within 3 business days"),
        (2,  1, "2023-08-22", "Technical", "Login issues after password reset",            "Resolved",    "Medium", "Account unlocked, password reset link sent"),
        (3,  1, "2024-01-15", "Product",   "Feature not working on mobile app",            "In Progress", "Low",    "Engineering team investigating"),
        (4,  1, "2024-03-01", "Billing",   "Request for invoice for tax purposes",         "Resolved",    "Low",    "Invoice sent via email"),
        # Robert Chen (2)
        (5,  2, "2023-09-05", "Technical", "API integration errors",                       "Resolved",    "High",   "Configuration guide provided"),
        (6,  2, "2024-02-14", "Billing",   "Upgrade plan request",                         "Resolved",    "Low",    "Plan upgraded to Premium"),
        # Alice Brown (3)
        (7,  3, "2022-12-10", "Account",   "Cancel subscription request",                  "Resolved",    "High",   "Subscription cancelled, refund processed"),
        (8,  3, "2023-01-20", "Billing",   "Final invoice request",                        "Resolved",    "Low",    "Final invoice sent"),
        # Michael Davis (4)
        (9,  4, "2023-11-12", "Technical", "SSO configuration assistance",                 "Resolved",    "High",   "IT team guided through SAML setup"),
        (10, 4, "2024-01-28", "Product",   "Custom reporting feature request",             "Open",        "Medium", "Added to product roadmap Q3 2024"),
        (11, 4, "2024-03-10", "Account",   "Add team members to account",                  "Resolved",    "Low",    "5 new users added to enterprise account"),
        # Sarah Wilson (5)
        (12, 5, "2023-10-05", "Technical", "Cannot access dashboard",                      "Resolved",    "High",   "Browser cache issue identified and resolved"),
        # James Martinez (6)
        (13, 6, "2023-06-20", "Billing",   "Discount for annual plan",                     "Resolved",    "Medium", "15% discount applied for annual commitment"),
        (14, 6, "2024-02-08", "Product",   "Data export functionality not working",        "Resolved",    "Medium", "Bug fixed in latest update v2.3.1"),
        # Emily Taylor (7)
        (15, 7, "2023-12-01", "Account",   "GDPR data deletion request",                   "Resolved",    "High",   "Data purged within 30-day SLA"),
        (16, 7, "2024-03-05", "Technical", "Performance issues with large datasets",        "In Progress", "High",   "Infrastructure team scaling database"),
        # David Anderson (8)
        (17, 8, "2024-01-10", "Billing",   "Wrong plan activated on signup",               "Resolved",    "Medium", "Plan corrected, difference refunded"),
        # Kevin Jackson (10)
        (18, 10, "2023-07-15", "Technical","Mobile app crashes on iOS 17",                  "Resolved",    "High",   "Patch released in v1.8.2"),
        (19, 10, "2024-02-20", "Product",  "Request for dark mode",                        "Open",        "Low",    "Feature request logged"),
    ]

    cursor.executemany(
        "INSERT INTO support_tickets VALUES (?,?,?,?,?,?,?,?)",
        tickets
    )

    conn.commit()
    conn.close()

    print("✅ Database created successfully!")
    print(f"   📊 {len(customers)} customers")
    print(f"   🎫 {len(tickets)} support tickets")
    print(f"   📁 Saved to: {DB_PATH}")


if __name__ == "__main__":
    create_database()
