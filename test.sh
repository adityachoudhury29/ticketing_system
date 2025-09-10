# curl -X 'POST' \
#   'http://localhost:8000/bookings/' \
#   -H 'accept: application/json' \
#   -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbkBldmVudGx5LmNvbSIsImV4cCI6MTc1NzQ5MTM0Nn0.dpMUoVVdXZDOgaRUdD6OzEMAkKcQRv9IO9rN1l0dP8g' \
#   -H 'Content-Type: application/json' \
#   -d '{
#   "event_id": 1,
#   "seat_identifiers": [
#     "A01-01"
#   ]
# }'

curl -X 'GET' \
  'http://localhost:8000/waitlist/my-entries?skip=0&limit=100' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhY2hvdWRodXJ5MjAwNEBnbWFpbC5jb20iLCJleHAiOjE3NTc0OTExMjB9.qVE0khRr5SyqrlDYbJGBa1jz43UenlobKTodGoUbLQs'

# user:  eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhY2hvdWRodXJ5MjAwNEBnbWFpbC5jb20iLCJleHAiOjE3NTc0OTExMjB9.qVE0khRr5SyqrlDYbJGBa1jz43UenlobKTodGoUbLQs'