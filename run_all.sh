#!/bin/sh

cd "$(dirname "$0")" || exit 1

FORCE=0
START=1
END=26
POS=0

for arg in "$@"; do
    if [ "$arg" = "--force" ]; then
        FORCE=1
    else
        POS=$((POS + 1))
        if [ "$POS" -eq 1 ]; then
            START=$arg
        elif [ "$POS" -eq 2 ]; then
            END=$arg
        fi
    fi
done

mkdir -p logs

FAILED=""
SKIPPED=""
COUNT_OK=0
COUNT_SKIP=0
COUNT_FAIL=0

n=$START
while [ "$n" -le "$END" ]; do
    if [ "$FORCE" -eq 0 ] && [ -f "tasks_$n.json" ] && [ -f "tasks_$n.html" ]; then
        echo "[$(date '+%H:%M:%S')] Задача $n: файлы уже есть, пропуск (перезапуск с --force)"
        SKIPPED="$SKIPPED $n"
        COUNT_SKIP=$((COUNT_SKIP + 1))
        n=$((n + 1))
        continue
    fi

    echo "[$(date '+%H:%M:%S')] Задача $n: загрузка из API (лог: logs/task_$n.log)"
    python3 shkolkovo_task_loader.py "$n" >> "logs/task_$n.log" 2>&1
    load_status=$?
    if [ "$load_status" -ne 0 ]; then
        echo "[$(date '+%H:%M:%S')] Задача $n: ошибка загрузки (код $load_status)"
        tail -n 15 "logs/task_$n.log"
        FAILED="$FAILED $n:load"
        COUNT_FAIL=$((COUNT_FAIL + 1))
        n=$((n + 1))
        continue
    fi

    echo "[$(date '+%H:%M:%S')] Задача $n: генерация HTML"
    python3 shkolkovo_make_html.py "$n" >> "logs/task_$n.log" 2>&1
    html_status=$?
    if [ "$html_status" -ne 0 ]; then
        echo "[$(date '+%H:%M:%S')] Задача $n: ошибка генерации HTML (код $html_status)"
        tail -n 15 "logs/task_$n.log"
        FAILED="$FAILED $n:html"
        COUNT_FAIL=$((COUNT_FAIL + 1))
        n=$((n + 1))
        continue
    fi

    echo "[$(date '+%H:%M:%S')] Задача $n: готово"
    COUNT_OK=$((COUNT_OK + 1))
    n=$((n + 1))
done

TOTAL=$((END - START + 1))
echo
echo "Итог: всего $TOTAL, обработано $COUNT_OK, пропущено $COUNT_SKIP, ошибок $COUNT_FAIL"
if [ -n "$FAILED" ]; then
    echo "Задачи с ошибками:$FAILED"
    exit 1
fi
echo "Все задачи диапазона $START-$END обработаны успешно"