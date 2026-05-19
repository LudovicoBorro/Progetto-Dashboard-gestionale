from datetime import datetime, timedelta
import holidays

def convert_datetime_to_working_days(start_date: datetime, target_date: datetime) -> int:
    today_date = datetime.now()
    holidays_list = holidays.IT()
    start_date = max(start_date.date(), today_date.date())
    target_date = target_date.date()
    days = (target_date - start_date).days
    working_days = 0
    for i in range(days):
        if start_date + timedelta(days=i) not in holidays_list and (start_date + timedelta(days=i)).weekday() < 5:
            working_days += 1
    return working_days

def convert_working_days_to_datetime(start_date: datetime, working_days: int) -> datetime:
    today_date = datetime.now()
    holidays_list = holidays.IT()
    current_date = max(start_date.date(), today_date.date())
    added_days = 0
    while added_days < working_days:
        current_date += timedelta(days=1)

        if current_date.weekday() < 5 and current_date not in holidays_list:
            added_days += 1
    return current_date

def generate_working_dates(start_date: datetime, num_days: int, from_today: bool = False) -> list[datetime]:
    """
    Genera una lista di date lavorative a partire da una data di inizio.
    Args:
        start_date (datetime): Data di inizio.
        num_days (int): Numero di giorni da generare.
        from_today (bool): Se True, considera solo i giorni a partire da oggi.
    Returns:
        list[datetime]: Lista di date lavorative.
    """
    italian_holidays = holidays.IT()
    dates = []
    if from_today:
        current_date = max(start_date.date(), datetime.now().date())
    else:
        current_date = start_date.date()
    while len(dates) < num_days:
        if current_date.weekday() < 5 and current_date not in italian_holidays:
            dates.append(current_date)
        current_date += timedelta(days=1)
    return dates


