# -*- coding: utf-8 -*-
"""
Created on Wed Aug 27 12:00:06 2025

@author: olve
"""

# -*- coding: utf-8 -*-
"""
Created on Wed Aug 27 11:29:51 2025

@author: olve
"""

# -*- coding: utf-8 -*-
"""
Created on Wed Aug 27 10:08:52 2025

@author: olve
"""

import asyncio
from telethon import TelegramClient
import re
from datetime import datetime
import pandas as pd
import os
import json

# --- Налаштування Telegram API ---
API_ID = os.environ.get('TELEGRAM_API_ID')
API_HASH = os.environ.get('TELEGRAM_API_HASH')
CHANNEL_ID = -4914800011

# --- Функції для парсингу даних ---
def parse_daily_report(report_text):
    """
    Парсить щоденний звіт і витягує всі деталі.
    """
    date_match = re.search(r'(?:Звіт|ЗВІТ)\s*[:\s]*(\d{1,2}\.\d{2}(?:\.\d{2,4})?)', report_text, re.IGNORECASE)
    if not date_match:
        return None
    
    try:
        report_date_str = date_match.group(1)
        if len(report_date_str.split('.')) < 3:
            report_date_str += '.' + str(datetime.now().year)
        report_date = datetime.strptime(report_date_str.strip('.'), '%d.%m.%Y').date()
    except ValueError:
        return None

    lines = [line.strip() for line in report_text.strip().split('\n') if line.strip()]
    data = []
    
    master_names = ['Наталія', 'Наталя', 'Віта', 'Інна', 'Антоніна', 'Оля', 'Ангеліна', 'Валерія', 'Наталка адмін']
    master_names_regex = r'|'.join(master_names)
    payment_methods_regex = r'(Готівка|Карта|На рахунок|готівка|карта|термінал)'
    
    current_master = None
    
    # Витягуємо підсумок
    reported_daily_revenue = None
    reported_total_match = re.search(r'(?:Всього за день|Виручка|Разом)(?:\s*[:\s]*)([\d\s\.,]+)\s*(?:грн|\(термінал\))', report_text, re.IGNORECASE)
    if reported_total_match:
        try:
            reported_daily_revenue = float(reported_total_match.group(1).replace(' ', '').replace(',', '.'))
        except (ValueError, IndexError):
            pass

    for i, line in enumerate(lines):
        # Оновлюємо поточного майстра, якщо рядок містить лише його ім'я
        if re.search(r'^{}$'.format(master_names_regex), line.strip(), re.IGNORECASE):
            current_master = line.strip()
            continue
        
        # Ігноруємо підсумкові рядки, щоб не парсити їх як транзакції
        if any(keyword in line for keyword in ["Всього за день", "Залишок", "Виручка", "Разом"]):
            continue

        master_match = re.search(master_names_regex, line, re.IGNORECASE)
        revenue_match = re.search(r'(-?\s*\d[\d\s\.,]*)[\s]*(?:грн|\(термінал\))', line, re.IGNORECASE)
        payment_match = re.search(payment_methods_regex, line, re.IGNORECASE)
        
        # Обробка витрат
        if "Витрати :" in line:
            revenue_line_match = re.search(r'(-?\s*\d[\d\s\.,]*)[\s]*(?:грн)', ' '.join(lines[i:]), re.IGNORECASE)
            if revenue_line_match:
                try:
                    revenue_str = revenue_line_match.group(1).replace(' ', '').replace(',', '.')
                    revenue = abs(float(revenue_str))
                    data.append({
                        'Date': report_date,
                        'Section': "Expenses",
                        'Client': None,
                        'Master': None,
                        'Service': "Витрати",
                        'Revenue': -revenue,
                        'PaymentMethod': None
                    })
                except (ValueError, IndexError):
                    pass
            continue
        
        # Обробка записів про послуги та продажі
        if revenue_match:
            try:
                revenue_str = revenue_match.group(1).replace(' ', '').replace(',', '.')
                revenue = abs(float(revenue_str))
            except (ValueError, IndexError):
                revenue = 0.0
            
            # Визначення розділу
            if "Продаж косметики:" in line:
                section = "Cosmetics Sale"
            elif "Продаж сертифікату" in line:
                section = "Certificate Sale"
            elif "На рахунок :" in line:
                section = "On Account"
            elif "по курсу" in line:
                section = "Course"
            else:
                section = "Service"
            
            # Визначення клієнта та послуги
            line_cleaned = re.sub(r'(\d{1,2}:\d{2})', '', line).strip()
            
            # Видалення суми та типу оплати з рядка послуги
            service_raw = re.sub(r'(-?\s*\d[\d\s\.,]*)\s*(?:грн|\(термінал\))', '', line_cleaned, re.IGNORECASE).strip()
            service_raw = re.sub(payment_methods_regex, '', service_raw, re.IGNORECASE).strip()
            
            parts = service_raw.split('-')
            client = parts[0].strip() if len(parts) > 0 else 'N/A'
            service = parts[1].strip() if len(parts) > 1 else client
            
            # Додаткове очищення послуги
            service = re.sub(r'по курсу', '', service, re.IGNORECASE).strip()
            service = re.sub(r'Продаж косметики:', '', service, re.IGNORECASE).strip()
            service = re.sub(r'Продаж сертифікату', '', service, re.IGNORECASE).strip()
            
            # Визначення майстра
            if master_match:
                master = master_match.group(1)
            else:
                master = current_master
            
            payment_method = payment_match.group(1) if payment_match else None
            
            data.append({
                'Date': report_date,
                'Section': section,
                'Client': client,
                'Master': master,
                'Service': service,
                'Revenue': revenue,
                'PaymentMethod': payment_method
            })
    
    # Додаємо рядок з підсумком дня
    data.append({
        'Date': report_date,
        'Section': 'Summary',
        'Client': None,
        'Master': None,
        'Service': 'Всього за день',
        'Revenue': reported_daily_revenue,
        'PaymentMethod': None
    })

    df = pd.DataFrame(data)
    return df

# --- Основна асинхронна функція для збору даних ---
async def main():
    print("Запускаємо збір даних з Telegram...")
    
    client_name = 'salon_session'
    client = TelegramClient(client_name, API_ID, API_HASH)

    if os.path.exists(f'{client_name}.session'):
        print("Використовуємо збережену сесію.")
    else:
        print("Сесія не знайдена. Потрібна авторизація. Будь ласка, введіть ваш номер телефону.")

    await client.start()
    
    try:
        if not await client.is_user_authorized():
            print("Авторизація не вдалася. Будь ласка, запустіть скрипт знову.")
            return

        print("\nПідключення успішне! Збираємо звіти...")
        reports_data = [] 
        reports_found = 0
        
        if os.path.exists('all_reports.csv'):
            os.remove('all_reports.csv')
            print("Видалено старий файл 'all_reports.csv'.")
            
        offset_id = 0
        limit_per_request = 100 
        
        while True:
            messages = await client.get_messages(CHANNEL_ID, limit=limit_per_request, offset_id=offset_id)
            if not messages:
                break 

            for message in messages:
                if message.text and re.search(r'(?:Звіт|ЗВІТ)', message.text, re.IGNORECASE):
                    try:
                        daily_df = parse_daily_report(message.text)
                        if daily_df is not None and not daily_df.empty:
                            reports_data.append(daily_df)
                            reports_found += 1
                        
                    except Exception as e:
                        print(f"Помилка при обробці звіту від {message.date} (ID: {message.id}): {e}")
            
            if not messages:
                break
            
            offset_id = messages[-1].id
            print(f"Отримано {len(messages)} повідомлень. Новий offset_id: {offset_id}. Продовжуємо...")

        if reports_data:
            all_reports_df = pd.concat(reports_data, ignore_index=True)
            all_reports_df.to_csv('all_reports.csv', index=False, encoding='utf-8-sig')
            print(f"\n✅ Завершено. Знайдено та збережено {reports_found} звітів у файл 'all_reports.csv'.")
        else:
            print("\n✅ Завершено. Звітів не знайдено.")

    except Exception as e:
        print(f"❌ Критична помилка: {e}")
    finally:
        await client.disconnect()
        
if __name__ == '__main__':
    asyncio.run(main())