import streamlit as st
import pandas as pd
from database import supabase
from saas_billing import generate_saas_invoice

# Page configuration
st.set_page_config(page_title="School SaaS Admin & Portal", page_icon="🏫", layout="wide")

st.title("🏫 School Fees Admin & SaaS Portal")
st.write("Automated Payment Reconciliation, Dedicated Virtual Accounts & SaaS Billing Engine")

# Fetch live data from Supabase
def load_data():
    students_res = supabase.table("students").select("*").execute()
    payments_res = supabase.table("payments").select("*").execute()
    clients_res = supabase.table("saas_clients").select("*").execute()
    
    df_students = pd.DataFrame(students_res.data) if students_res.data else pd.DataFrame()
    df_payments = pd.DataFrame(payments_res.data) if payments_res.data else pd.DataFrame()
    df_clients = pd.DataFrame(clients_res.data) if clients_res.data else pd.DataFrame()
    
    return df_students, df_payments, df_clients

df_students, df_payments, df_clients = load_data()

# Render Dashboard Navigation Tabs
tab1, tab2 = st.tabs(["📊 School Operations", "💳 SaaS Subscription & Billing"])

# --- TAB 1: SCHOOL FEE RECONCILIATION ---
with tab1:
    st.divider()
    col1, col2, col3 = st.columns(3)

    with col1:
        total_students = len(df_students)
        st.metric("Total Registered Students", total_students)

    with col2:
        total_revenue = df_payments["amount_paid"].sum() if not df_payments.empty else 0
        st.metric("Total School Fees Collected", f"₦{total_revenue:,.2f}")

    with col3:
        total_transactions = len(df_payments)
        st.metric("Successful Transactions", total_transactions)

    st.divider()

    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("📋 Recent Fee Payments")
        if not df_payments.empty:
            if not df_students.empty:
                df_students_clean = df_students[["id", "student_name"]]
                df_merged = df_payments.merge(df_students_clean, left_on="student_id", right_on="id", how="left")
                
                if "created_at" in df_merged.columns:
                    display_df = df_merged[["student_name", "amount_paid", "transaction_reference", "created_at"]]
                    display_df.columns = ["Student", "Amount (₦)", "Reference", "Date"]
                else:
                    display_df = df_merged[["student_name", "amount_paid", "transaction_reference"]]
                    display_df.columns = ["Student", "Amount (₦)", "Reference"]
                    
                st.dataframe(display_df, use_container_width=True, hide_index=True)
            else:
                st.dataframe(df_payments, use_container_width=True)
        else:
            st.info("No payments recorded yet.")

    with col_b:
        st.subheader("🎓 Registered Students & Virtual Accounts")
        if not df_students.empty:
            dva_df = df_students[["student_name", "student_class", "account_number", "bank_name"]].copy()
            dva_df["account_number"] = dva_df["account_number"].astype(str)
            dva_df.columns = ["Name", "Class", "Virtual Account Number", "Bank"]
            st.dataframe(dva_df, use_container_width=True, hide_index=True)
        else:
            st.info("No students registered yet.")

    if st.button("🔄 Refresh Data"):
        st.rerun()

# --- TAB 2: SAAS MULTI-TENANT PER-STUDENT BILLING ---
with tab2:
    st.subheader("💳 SaaS Software Subscription")
    st.write("Per-Student Billing Management for School Administrators")

    if not df_clients.empty:
        client_info = df_clients.iloc[0]
        school_name = str(client_info["school_name"])
        admin_email = str(client_info["admin_email"])
        student_count = int(client_info["student_count"])
        fee_per_student = int(client_info.get("fee_per_student_usd", 1500))
        if fee_per_student == 1:  # Fallback to NGN rate if default 1 was stored
            fee_per_student = 1500
    else:
        school_name = "Maypride Secondary School"
        admin_email = "maypridenps2006@yahoo.co.uk"
        student_count = 350
        fee_per_student = 1500

    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        st.metric("School", school_name)
    with col_s2:
        st.metric("Active Enrolled Students", student_count)
    with col_s3:
        total_due = student_count * fee_per_student
        st.metric("Term Invoice Total", f"₦{total_due:,.2f}")

    st.divider()
    st.markdown(f"**Rate Schedule:** {student_count} Enrolled Students × ₦{fee_per_student:,} / student = **₦{total_due:,} per term**")

    if st.button("🚀 Pay Term Subscription via Paystack"):
        payment_url = generate_saas_invoice(
            school_name=school_name,
            admin_email=admin_email,
            student_count=student_count,
            fee_per_student=fee_per_student
        )
        if payment_url:
            st.success("Invoice initialized successfully!")
            st.markdown(f"👉 **[Click Here to Complete ₦{total_due:,} Payment on Paystack]({payment_url})**")
        else:
            st.error("Could not generate Paystack payment link. Verify API keys.")