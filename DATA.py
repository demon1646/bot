import datetime

current_date = datetime.date.today()

week_number = current_date.isocalendar()[1]

day_of_week = current_date.weekday()

days = ['понедельник', 'вторник', 'среда', 'четверг', 'пятница']

print(f"Номер недели: {week_number}")
print(f"День недели: {days[day_of_week]}")
