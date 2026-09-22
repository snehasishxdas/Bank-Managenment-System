"""Core banking logic for Python Bank Management.

This module intentionally keeps persistence simple (a JSON file) so it is easy
to learn from.  Do not use JSON storage for a real bank: use an audited
database, proper identity verification, encryption, and professional security
reviews.
"""
from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any


class BankError(Exception):
    """A friendly error raised for invalid banking actions."""


class PythonBankManagement:
    """Object-oriented service layer backed by one JSON data file."""

    def __init__(self, data_file: str | Path = "data.json", bank_name: str = "Python Bank Management"):
        self.data_file = Path(data_file)
        self.bank_name = bank_name
        self._ensure_data_file()

    # ---------- Storage and helpers ----------
    def _empty_data(self) -> dict[str, Any]:
        return {"bank_name": self.bank_name, "customers": {}, "accounts": {}, "transactions": [], "loans": {}, "fixed_deposits": {}, "bills": {}, "beneficiaries": {}}

    def _ensure_data_file(self) -> None:
        if not self.data_file.exists():
            self._save(self._empty_data())

    def _load(self) -> dict[str, Any]:
        try:
            with self.data_file.open("r", encoding="utf-8") as file:
                return json.load(file)
        except (json.JSONDecodeError, OSError) as error:
            raise BankError("Unable to read data.json. Check that it contains valid JSON.") from error

    def _save(self, data: dict[str, Any]) -> None:
        # Atomic replacement prevents a half-written file in ordinary use.
        temporary = self.data_file.with_suffix(".tmp")
        with temporary.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
        temporary.replace(self.data_file)

    @staticmethod
    def _hash_password(password: str) -> str:
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    @staticmethod
    def _money(amount: float | str) -> float:
        try:
            value = round(float(amount), 2)
        except (ValueError, TypeError) as error:
            raise BankError("Amount must be a valid number.") from error
        if value <= 0:
            raise BankError("Amount must be greater than zero.")
        return value

    @staticmethod
    def _now() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _new_id(prefix: str) -> str:
        return f"{prefix}-{uuid.uuid4().hex[:10].upper()}"

    def _account(self, data: dict[str, Any], account_number: str) -> dict[str, Any]:
        account = data["accounts"].get(account_number)
        if not account:
            raise BankError("Account number was not found.")
        if account["status"] != "Active":
            raise BankError("This account is not active.")
        return account

    def _record(self, data: dict[str, Any], kind: str, amount: float, account_number: str, note: str, counterparty: str = "") -> None:
        data["transactions"].append({"id": self._new_id("TXN"), "timestamp": self._now(), "type": kind, "amount": amount, "account_number": account_number, "counterparty": counterparty, "note": note})

    # ---------- Customer and account operations ----------
    def register_customer(self, full_name: str, email: str, phone: str, password: str, opening_balance: float = 0, account_type: str = "Savings") -> str:
        if not all([full_name.strip(), email.strip(), phone.strip()]):
            raise BankError("Name, email, and phone are required.")
        if len(password) < 6:
            raise BankError("Password must contain at least 6 characters.")
        if opening_balance < 0:
            raise BankError("Opening balance cannot be negative.")
        data = self._load()
        if any(c["email"].lower() == email.strip().lower() for c in data["customers"].values()):
            raise BankError("An account with this email already exists.")
        customer_id, account_number = self._new_id("CUS"), "PB" + secrets.token_hex(5).upper()
        data["customers"][customer_id] = {"id": customer_id, "full_name": full_name.strip(), "email": email.strip().lower(), "phone": phone.strip(), "password_hash": self._hash_password(password), "created_at": self._now()}
        data["accounts"][account_number] = {"account_number": account_number, "customer_id": customer_id, "type": account_type, "balance": round(float(opening_balance), 2), "status": "Active", "created_at": self._now()}
        if opening_balance:
            self._record(data, "Opening Deposit", float(opening_balance), account_number, "Initial account funding")
        self._save(data)
        return account_number

    def authenticate(self, email: str, password: str) -> dict[str, Any] | None:
        data = self._load()
        password_hash = self._hash_password(password)
        for customer in data["customers"].values():
            if customer["email"] == email.strip().lower() and customer["password_hash"] == password_hash:
                return {key: value for key, value in customer.items() if key != "password_hash"}
        return None

    def customer_accounts(self, customer_id: str) -> list[dict[str, Any]]:
        data = self._load()
        return [account for account in data["accounts"].values() if account["customer_id"] == customer_id]

    def dashboard(self, customer_id: str) -> dict[str, Any]:
        accounts = self.customer_accounts(customer_id)
        return {"accounts": accounts, "total_balance": round(sum(a["balance"] for a in accounts), 2), "recent_transactions": [t for t in reversed(self._load()["transactions"]) if t["account_number"] in {a["account_number"] for a in accounts}][:8]}

    def deposit(self, account_number: str, amount: float, note: str = "Cash deposit") -> None:
        amount = self._money(amount); data = self._load(); account = self._account(data, account_number)
        account["balance"] = round(account["balance"] + amount, 2); self._record(data, "Deposit", amount, account_number, note); self._save(data)

    def withdraw(self, account_number: str, amount: float, note: str = "Cash withdrawal") -> None:
        amount = self._money(amount); data = self._load(); account = self._account(data, account_number)
        if account["balance"] < amount: raise BankError("Insufficient available balance.")
        account["balance"] = round(account["balance"] - amount, 2); self._record(data, "Withdrawal", amount, account_number, note); self._save(data)

    def transfer(self, sender: str, recipient: str, amount: float, note: str = "Bank transfer") -> None:
        amount = self._money(amount)
        if sender == recipient: raise BankError("Choose a different recipient account.")
        data = self._load(); source, target = self._account(data, sender), self._account(data, recipient)
        if source["balance"] < amount: raise BankError("Insufficient available balance.")
        source["balance"] = round(source["balance"] - amount, 2); target["balance"] = round(target["balance"] + amount, 2)
        self._record(data, "Transfer Sent", amount, sender, note, recipient); self._record(data, "Transfer Received", amount, recipient, note, sender); self._save(data)

    def add_beneficiary(self, customer_id: str, name: str, account_number: str) -> None:
        data = self._load(); self._account(data, account_number)
        items = data["beneficiaries"].setdefault(customer_id, [])
        if not any(b["account_number"] == account_number for b in items): items.append({"name": name.strip(), "account_number": account_number})
        self._save(data)

    def beneficiaries(self, customer_id: str) -> list[dict[str, str]]:
        return self._load()["beneficiaries"].get(customer_id, [])

    # ---------- Everyday banking products ----------
    def pay_bill(self, customer_id: str, account_number: str, biller: str, amount: float) -> None:
        amount = self._money(amount); data = self._load(); account = self._account(data, account_number)
        if account["customer_id"] != customer_id: raise BankError("You can only use your own account.")
        if account["balance"] < amount: raise BankError("Insufficient available balance.")
        account["balance"] = round(account["balance"] - amount, 2); bill = {"id": self._new_id("BILL"), "biller": biller, "amount": amount, "paid_at": self._now(), "account_number": account_number}
        data["bills"].setdefault(customer_id, []).append(bill); self._record(data, "Bill Payment", amount, account_number, f"Paid {biller}"); self._save(data)

    def apply_loan(self, customer_id: str, amount: float, purpose: str, months: int) -> str:
        amount = self._money(amount)
        if months not in range(1, 121): raise BankError("Loan term must be between 1 and 120 months.")
        data = self._load(); loan_id = self._new_id("LOAN")
        # Demonstration fixed rate, not lending advice.
        data["loans"][loan_id] = {"id": loan_id, "customer_id": customer_id, "amount": amount, "purpose": purpose.strip(), "months": months, "annual_rate": 10.0, "status": "Pending", "applied_at": self._now()}
        self._save(data); return loan_id

    def open_fixed_deposit(self, customer_id: str, account_number: str, amount: float, months: int) -> str:
        amount = self._money(amount)
        if months not in range(1, 121): raise BankError("Deposit term must be between 1 and 120 months.")
        data = self._load(); account = self._account(data, account_number)
        if account["customer_id"] != customer_id: raise BankError("You can only use your own account.")
        if account["balance"] < amount: raise BankError("Insufficient available balance.")
        account["balance"] = round(account["balance"] - amount, 2); fd_id = self._new_id("FD")
        data["fixed_deposits"][fd_id] = {"id": fd_id, "customer_id": customer_id, "source_account": account_number, "principal": amount, "months": months, "annual_rate": 6.5, "opened_at": self._now(), "maturity_date": date.fromordinal(date.today().toordinal() + months * 30).isoformat(), "status": "Active"}
        self._record(data, "Fixed Deposit", amount, account_number, f"Fixed deposit {fd_id}"); self._save(data); return fd_id

    def customer_products(self, customer_id: str) -> dict[str, list[dict[str, Any]]]:
        data = self._load()
        return {"loans": [x for x in data["loans"].values() if x["customer_id"] == customer_id], "fixed_deposits": [x for x in data["fixed_deposits"].values() if x["customer_id"] == customer_id], "bills": data["bills"].get(customer_id, [])}
