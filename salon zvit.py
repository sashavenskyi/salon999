# -*- coding: utf-8 -*-
"""
Created on Wed Aug 27 11:41:13 2025

@author: olve
"""

# -*- coding: utf-8 -*-
"""
Created on Tue Aug 26 16:56:39 2025

@author: olve
"""

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import numpy as np

# Завантаження даних
@st.cache_data
def load_data(file_path):
    if not os.path.exists(file_path):
        st.error(f"Файл '{file_path}' не знайдено. Будь ласка, запустіть скрипт 'telegram_collector.py' для збору даних.")
        return pd.DataFrame()
    try:
        df = pd.read_csv(file_path, encoding='utf-8-sig')
        df['Revenue'] = pd.to_numeric(df['Revenue'], errors='coerce')
        return df
    except Exception as e:
        st.error(f"Помилка при завантаженні файлу: {e}")
        return pd.DataFrame()

# Завантажуємо дані
df_raw = load_data('all_reports.csv')

if not df_raw.empty:
    df_raw['Date'] = pd.to_datetime(df_raw['Date'], errors='coerce')
    df_raw.dropna(subset=['Date'], inplace=True)
    
    # Сортування даних за датою
    df_raw.sort_values(by='Date', inplace=True)
    
    st.title("Фінансовий звіт салону краси Venska Easy Body Lutsk")
    st.markdown("---")

    # Фільтрація за датою
    min_date = df_raw['Date'].min().date()
    max_date = df_raw['Date'].max().date()
    
    date_range = st.sidebar.date_input("Виберіть діапазон дат", [min_date, max_date])

    if len(date_range) == 2:
        start_date, end_date = date_range
        filtered_df = df_raw[(df_raw['Date'].dt.date >= start_date) & (df_raw['Date'].dt.date <= end_date)].copy()
    else:
        st.warning("Будь ласка, виберіть початок і кінець діапазону дат.")
        filtered_df = pd.DataFrame()
        
    if not filtered_df.empty:
        # Видаляємо рядки з підсумками, щоб уникнути подвійного підрахунку
        transaction_df = filtered_df[filtered_df['Section'] != 'Summary']
        
        # Розрахунок загальних показників на основі Summary рядків
        total_revenue_from_summary = filtered_df[filtered_df['Section'] == 'Summary']['Revenue'].sum()
        total_expenses = filtered_df[filtered_df['Section'] == 'Expenses']['Revenue'].sum()
        net_profit = total_revenue_from_summary + total_expenses
        
        daily_summary = filtered_df[filtered_df['Section'] == 'Summary'][['Date', 'Revenue']].rename(columns={'Revenue': 'Всього за день (грн)'})
        average_daily_revenue = daily_summary['Всього за день (грн)'].mean()

        st.subheader("Загальні підсумки за вибраний період")
        st.metric(label="💰 Загальна виручка", value=f"{total_revenue_from_summary:,.0f} грн")
        st.metric(label="💸 Загальні витрати", value=f"{abs(total_expenses):,.0f} грн")
        st.metric(label="📈 Чистий прибуток", value=f"{net_profit:,.0f} грн")
        st.metric(label="📊 Середній дохід за день", value=f"{average_daily_revenue:,.0f} грн")
        st.markdown("---")
        
        # Підсумки за днями
        st.subheader("Підсумки за днями")
        st.dataframe(daily_summary.sort_values(by='Date'))
        st.markdown("---")

        ## Динаміка виручки
        st.header("Динаміка виручки")
        if not daily_summary.empty:
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.plot(daily_summary['Date'], daily_summary['Всього за день (грн)'], marker='o', linestyle='-', color='#007bff')
            ax.set_title('Щоденна виручка за вибраний період')
            ax.set_xlabel('Дата')
            ax.set_ylabel('Виручка (грн)')
            plt.xticks(rotation=45, ha='right')
            plt.grid(True)
            st.pyplot(fig)
        st.markdown("---")
        
        ## Розбивка доходу за типом оплати
        st.header("Розбивка доходу за типом оплати")
        
        # Приведення назв типів оплати до єдиного формату (title case)
        transaction_df['PaymentMethod'] = transaction_df['PaymentMethod'].str.title()
        
        payment_by_day = transaction_df.groupby([transaction_df['Date'].dt.date, 'PaymentMethod'])['Revenue'].sum().unstack(fill_value=0)
        
        if not payment_by_day.empty:
            # Словник з кольорами для кожного типу оплати
            payment_colors = {
                'Готівка': '#4CAF50', 
                'Карта': '#FFC107', 
                'На Рахунок': '#607D8B',
                'Термінал': '#FFC107',
                'Сертифікат': '#9C27B0'
            }
            # Створюємо список кольорів для графіка, використовуючи словник та назви колонок
            colors_list = [payment_colors.get(col, '#9E9E9E') for col in payment_by_day.columns]
            
            fig, ax = plt.subplots(figsize=(12, 8))
            payment_by_day.plot(kind='bar', stacked=True, ax=ax, color=colors_list)
            ax.set_title('Розбивка виручки за типом оплати (по днях)')
            ax.set_xlabel('Дата')
            ax.set_ylabel('Виручка (грн)')
            plt.xticks(rotation=45, ha='right')
            plt.legend(title='Тип оплати')
            st.pyplot(fig)
        st.markdown("---")
        
        ## Дохід за днями тижня (Теплова карта)
        st.header("Дохід за днями тижня")
        daily_summary['DayOfWeek'] = daily_summary['Date'].dt.day_name()
        daily_summary['WeekNumber'] = daily_summary['Date'].dt.isocalendar().week.astype('int64')

        # Переклад днів тижня
        day_names_map = {
            'Monday': 'Понеділок',
            'Tuesday': 'Вівторок',
            'Wednesday': 'Середа',
            'Thursday': 'Четвер',
            'Friday': 'Пʼятниця',
            'Saturday': 'Субота',
            'Sunday': 'Неділя'
        }
        daily_summary['DayOfWeek'] = daily_summary['DayOfWeek'].map(day_names_map)
        
        heatmap_data = daily_summary.pivot_table(index='DayOfWeek', columns='WeekNumber', values='Всього за день (грн)', aggfunc='sum')
        
        # Сортування днів тижня
        sorted_days = ['Понеділок', 'Вівторок', 'Середа', 'Четвер', 'Пʼятниця', 'Субота', 'Неділя']
        heatmap_data = heatmap_data.reindex(sorted_days)

        fig, ax = plt.subplots(figsize=(12, 8))
        sns.heatmap(heatmap_data, annot=True, fmt=".0f", cmap="YlGnBu", linewidths=.5, ax=ax)
        ax.set_title('Дохід за днями тижня (грн)')
        ax.set_xlabel('Номер тижня')
        ax.set_ylabel('День тижня')
        st.pyplot(fig)
        st.markdown("---")

        # Огляд всіх даних
        st.header("Огляд даних")
        st.dataframe(filtered_df)
        st.markdown("---")
        
        ## KPIs за майстрами
        st.header("Показники ефективності (KPI) за майстрами")
        master_kpis = transaction_df[
            (transaction_df['Section'] != 'Expenses')
        ].groupby('Master').agg(
            Total_Revenue=('Revenue', 'sum'),
            Total_Transactions=('Revenue', 'count')
        ).reset_index()

        master_kpis['Average_Transaction'] = master_kpis['Total_Revenue'] / master_kpis['Total_Transactions']
        master_kpis = master_kpis.sort_values(by='Total_Revenue', ascending=False)
        
        st.subheader("Дохід та середня вартість послуги")
        st.dataframe(master_kpis.rename(columns={
            'Master': 'Майстер',
            'Total_Revenue': 'Загальний дохід (грн)',
            'Total_Transactions': 'Кількість транзакцій',
            'Average_Transaction': 'Середня вартість послуги (грн)'
        }).style.format({
            'Загальний дохід (грн)': '{:,.0f}'.format,
            'Середня вартість послуги (грн)': '{:,.0f}'.format
        }))
        st.markdown("---")
        
        # Дохід за майстрами (горизонтальна діаграма)
        st.header("Дохід за майстрами")
        master_revenue = master_kpis.set_index('Master')['Total_Revenue']
        
        if not master_revenue.empty:
            fig, ax = plt.subplots(figsize=(10, 6))
            sns.barplot(y=master_revenue.index, x=master_revenue.values, ax=ax, orient='h')
            plt.ylabel("Майстер")
            plt.xlabel("Дохід (грн)")
            st.pyplot(fig)
        st.markdown("---")
        
        # Розподіл типів оплати (кругова діаграма)
        st.header("Розподіл типів оплати")
        payment_counts = transaction_df[
            (transaction_df['Section'] != 'Expenses')
        ].groupby('PaymentMethod')['Revenue'].sum().sort_values(ascending=False)
        
        if not payment_counts.empty:
            fig, ax = plt.subplots()
            ax.pie(payment_counts.values, labels=payment_counts.index, autopct='%1.1f%%', startangle=90)
            ax.axis('equal')
            st.pyplot(fig)
        st.markdown("---")

    else:
        st.warning("За вибраний період дані відсутні.")