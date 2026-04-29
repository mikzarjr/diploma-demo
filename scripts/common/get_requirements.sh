#!/bin/bash
# Использование: bash get_requirements.sh ../../app/backend

folder=$1

if [ -z "$folder" ]; then
  echo "❌ Укажите путь к папке, например:"
  echo "   bash get_requirements ../../app/backend"
  exit 1
fi

if ! command -v pipreqs &> /dev/null; then
  echo "❌ pipreqs не найден. Установи его командой:"
  echo "   pip install pipreqs"
  exit 1
fi

if [ ! -d "$folder" ]; then
  echo "❌ Папка '$folder' не найдена."
  exit 1
fi

echo "🔍 Анализирую зависимости в '$folder'..."
echo "----------------------------------------"

tmpfile=$(mktemp)
pipreqs "$folder" --print > "$tmpfile" 2>/dev/null

if [ ! -s "$tmpfile" ]; then
  echo "⚠️  В папке не найдено импортов Python."
  rm "$tmpfile"
  exit 0
fi

cat "$tmpfile"
echo "----------------------------------------"
echo "✅ Готово. Это зависимости, используемые в '$folder'."

rm "$tmpfile"

