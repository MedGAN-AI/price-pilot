FROM python:3.12-slim

WORKDIR /app

# comment them if you work with local env
ARG SUPABASE_URL
ARG SUPABASE_KEY
ARG GOOGLE_API_KEY

ENV SUPABASE_URL=$SUPABASE_URL
ENV SUPABASE_KEY=$SUPABASE_KEY
ENV GOOGLE_API_KEY=$GOOGLE_API_KEY

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
