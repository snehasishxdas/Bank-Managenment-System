import pandas as pd
import streamlit as st

from Bank import BankError, PythonBankManagement

st.set_page_config(page_title="Python Bank Management", page_icon=":material/account_balance:", layout="wide", initial_sidebar_state="expanded")
bank = PythonBankManagement()


def money(value: float) -> str:
    return f"₹{value:,.2f}"


def run_action(action, message="Your request has been completed."):
    try:
        action()
        st.toast(message, icon=":material/check_circle:")
    except BankError as error:
        st.error(str(error), icon=":material/error:")


def account_choices(accounts):
    return {f"{item['type']} • {item['account_number']} • {money(item['balance'])}": item["account_number"] for item in accounts}


def transaction_table(rows):
    if not rows:
        st.info("There are no transactions to show yet.", icon=":material/receipt_long:")
        return
    table = pd.DataFrame(rows).copy()
    table["amount"] = table["amount"].map(money)
    columns = [column for column in ["timestamp", "type", "amount", "account_number", "counterparty", "note"] if column in table]
    st.dataframe(table[columns], hide_index=True, width="stretch")


if "customer" not in st.session_state:
    st.session_state.customer = None

if not st.session_state.customer:
    st.space("medium")
    lead, mark = st.columns([5, 2], vertical_alignment="center")
    with lead:
        st.title("Banking that feels clear and simple", icon=":material/account_balance:")
        st.markdown(":blue-badge[PYTHON BANK MANAGEMENT]  :green-badge[Secure demo workspace]")
        st.write("Manage everyday money tasks, savings goals, and applications from one calm, modern dashboard.")
    with mark:
        with st.container(border=True):
            st.subheader("Your money, in view", icon=":material/insights:")
            st.caption("Accounts • Transfers • Bills • Savings")
    sign_in, open_account = st.tabs(["Sign in", "Open an account"])
    with sign_in:
        with st.container(border=True):
            st.subheader("Welcome back", icon=":material/login:")
            st.caption("Sign in to access your personal banking space.")
            with st.form("login_form"):
                email = st.text_input("Email address", placeholder="you@example.com")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Sign in securely", type="primary", width="stretch", icon=":material/login:")
            if submitted:
                customer = bank.authenticate(email, password)
                if customer:
                    st.session_state.customer = customer
                    st.rerun()
                st.error("Email or password is incorrect.", icon=":material/error:")
    with open_account:
        with st.container(border=True):
            st.subheader("Open your account", icon=":material/person_add:")
            st.caption("It takes less than a minute to get started.")
            with st.form("registration_form"):
                left, right = st.columns(2)
                with left:
                    name = st.text_input("Full name")
                    email = st.text_input("Email address", placeholder="you@example.com")
                    password = st.text_input("Password", type="password", help="Use at least 6 characters.")
                with right:
                    phone = st.text_input("Phone number")
                    account_type = st.selectbox("Account type", ["Savings", "Current"])
                    opening_balance = st.number_input("Opening balance", min_value=0.0, step=100.0, format="%.2f")
                submitted = st.form_submit_button("Create my account", type="primary", width="stretch", icon=":material/add_card:")
            if submitted:
                try:
                    number = bank.register_customer(name, email, phone, password, opening_balance, account_type)
                    st.success(f"Account created successfully. Your account number is {number}.", icon=":material/check_circle:")
                except BankError as error:
                    st.error(str(error), icon=":material/error:")
    st.stop()

customer = st.session_state.customer
overview = bank.dashboard(customer["id"])
accounts = overview["accounts"]
if not accounts:
    st.error("No active account was found for this profile.", icon=":material/error:")
    st.stop()
choices = account_choices(accounts)

with st.sidebar:
    st.title("Python Bank", icon=":material/account_balance:")
    st.caption("Personal banking portal")
    st.write(f"**{customer['full_name']}**")
    st.caption(customer["email"])
    page = st.radio("Navigate", ["Overview", "Transfer", "Cash services", "Bill payments", "Savings & loans", "Activity"], label_visibility="collapsed")
    st.space("large")
    if st.button("Sign out", icon=":material/logout:", width="stretch"):
        st.session_state.customer = None
        st.rerun()
    st.caption("Python Bank Management • Educational demo")

if page == "Overview":
    first_name = customer["full_name"].split()[0]
    st.title(f"Good to see you, {first_name}", icon=":material/waving_hand:")
    st.caption("Here is your latest account snapshot.")
    metric_one, metric_two, metric_three = st.columns(3)
    metric_one.metric("Total available balance", money(overview["total_balance"]), delta="Available now")
    metric_two.metric("Active accounts", len(accounts), delta="All accounts active")
    metric_three.metric("Recent transactions", len(overview["recent_transactions"]), delta="Last 8 records")
    main, side = st.columns([3, 2], vertical_alignment="top")
    with main:
        with st.container(border=True):
            st.subheader("Your accounts", icon=":material/account_balance_wallet:")
            account_data = pd.DataFrame(accounts)[["account_number", "type", "balance", "status", "created_at"]].copy()
            account_data["balance"] = account_data["balance"].map(money)
            st.dataframe(account_data, hide_index=True, width="stretch")
    with side:
        with st.container(border=True):
            st.subheader("Quick actions", icon=":material/bolt:")
            st.caption("Use the navigation menu to move money, make a payment, or grow your savings.")
            st.badge("All systems normal", icon=":material/check_circle:", color="green")
            st.space("small")
            st.caption("Tip: Add a beneficiary once, then reuse their account details for future transfers.")
    with st.container(border=True):
        st.subheader("Recent activity", icon=":material/receipt_long:")
        transaction_table(overview["recent_transactions"])

elif page == "Transfer":
    st.title("Transfer money", icon=":material/send_money:")
    st.caption("Send money between active Python Bank accounts.")
    left, right = st.columns([3, 2], vertical_alignment="top")
    with left:
        with st.container(border=True):
            st.subheader("New transfer", icon=":material/swap_horiz:")
            with st.form("transfer_form"):
                sender_label = st.selectbox("Pay from", choices.keys())
                recipient = st.text_input("Recipient account number", placeholder="PBXXXXXXXXXX")
                amount = st.number_input("Amount", min_value=1.0, step=100.0, format="%.2f")
                note = st.text_input("Reference", placeholder="Example: Rent for September")
                submitted = st.form_submit_button("Review and transfer", type="primary", width="stretch", icon=":material/send:")
            if submitted:
                run_action(lambda: bank.transfer(choices[sender_label], recipient.strip().upper(), amount, note or "Bank transfer"), "Transfer completed successfully.")
    with right:
        with st.container(border=True):
            st.subheader("Saved beneficiaries", icon=":material/group:")
            beneficiaries = bank.beneficiaries(customer["id"])
            if beneficiaries:
                st.dataframe(pd.DataFrame(beneficiaries), hide_index=True, width="stretch")
            else:
                st.caption("You have not saved a beneficiary yet.")
        with st.expander("Add a beneficiary", icon=":material/person_add:"):
            name = st.text_input("Beneficiary name")
            number = st.text_input("Account number", key="beneficiary_account")
            if st.button("Save beneficiary", icon=":material/bookmark_add:", width="stretch"):
                run_action(lambda: bank.add_beneficiary(customer["id"], name, number.strip().upper()), "Beneficiary saved.")

elif page == "Cash services":
    st.title("Cash services", icon=":material/payments:")
    st.caption("Record cash deposits and withdrawals on an active account.")
    deposit_panel, withdrawal_panel = st.columns(2, vertical_alignment="top")
    with deposit_panel:
        with st.container(border=True):
            st.subheader("Deposit funds", icon=":material/add_circle:")
            with st.form("deposit_form"):
                account = st.selectbox("Deposit to", choices.keys(), key="deposit_account")
                amount = st.number_input("Deposit amount", min_value=1.0, step=100.0, format="%.2f", key="deposit_amount")
                submitted = st.form_submit_button("Confirm deposit", type="primary", width="stretch")
            if submitted:
                run_action(lambda: bank.deposit(choices[account], amount), "Deposit recorded.")
    with withdrawal_panel:
        with st.container(border=True):
            st.subheader("Withdraw funds", icon=":material/remove_circle:")
            with st.form("withdrawal_form"):
                account = st.selectbox("Withdraw from", choices.keys(), key="withdrawal_account")
                amount = st.number_input("Withdrawal amount", min_value=1.0, step=100.0, format="%.2f", key="withdrawal_amount")
                submitted = st.form_submit_button("Confirm withdrawal", type="primary", width="stretch")
            if submitted:
                run_action(lambda: bank.withdraw(choices[account], amount), "Withdrawal recorded.")

elif page == "Bill payments":
    st.title("Pay a bill", icon=":material/receipt:")
    st.caption("Pay a household bill directly from your selected bank account.")
    with st.container(border=True):
        with st.form("bill_form"):
            left, right = st.columns(2)
            with left:
                account = st.selectbox("Pay from", choices.keys())
                biller = st.selectbox("Biller", ["Electricity", "Water", "Mobile recharge", "Internet", "Insurance", "Other"])
            with right:
                amount = st.number_input("Amount due", min_value=1.0, step=50.0, format="%.2f")
                st.caption("Payments are immediately recorded in your activity history.")
            submitted = st.form_submit_button("Pay bill", type="primary", width="stretch", icon=":material/payments:")
        if submitted:
            run_action(lambda: bank.pay_bill(customer["id"], choices[account], biller, amount), "Bill payment completed.")

elif page == "Savings & loans":
    st.title("Savings and loans", icon=":material/savings:")
    st.caption("Build savings with a fixed deposit or submit a loan request.")
    products = bank.customer_products(customer["id"])
    fixed_deposit, loan = st.tabs(["Fixed deposit", "Loan application"])
    with fixed_deposit:
        with st.container(border=True):
            st.subheader("Open a fixed deposit", icon=":material/lock:")
            with st.form("fd_form"):
                account = st.selectbox("Fund from", choices.keys())
                amount = st.number_input("Deposit amount", min_value=100.0, step=100.0, format="%.2f")
                months = st.slider("Term in months", 1, 120, 12)
                submitted = st.form_submit_button("Open fixed deposit", type="primary", width="stretch")
            if submitted:
                run_action(lambda: bank.open_fixed_deposit(customer["id"], choices[account], amount, months), "Fixed deposit opened.")
        if products["fixed_deposits"]:
            st.subheader("Your fixed deposits", icon=":material/folder_shared:")
            st.dataframe(pd.DataFrame(products["fixed_deposits"]), hide_index=True, width="stretch")
    with loan:
        with st.container(border=True):
            st.subheader("Apply for a loan", icon=":material/request_quote:")
            with st.form("loan_form"):
                amount = st.number_input("Requested amount", min_value=1000.0, step=1000.0, format="%.2f")
                purpose = st.text_input("Purpose", placeholder="Example: Education")
                months = st.slider("Repayment term in months", 1, 120, 24, key="loan_months")
                submitted = st.form_submit_button("Submit application", type="primary", width="stretch")
            if submitted:
                run_action(lambda: bank.apply_loan(customer["id"], amount, purpose, months), "Loan application submitted.")
        if products["loans"]:
            st.subheader("Your loan applications", icon=":material/description:")
            st.dataframe(pd.DataFrame(products["loans"]), hide_index=True, width="stretch")

else:
    st.title("Account activity", icon=":material/history:")
    st.caption("A complete record of transactions on your active accounts.")
    rows = [item for item in bank._load()["transactions"] if item["account_number"] in {account["account_number"] for account in accounts}]
    with st.container(border=True):
        transaction_table(list(reversed(rows)))
