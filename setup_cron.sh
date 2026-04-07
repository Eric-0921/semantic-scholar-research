#!/bin/bash
# 每日科研简报 Cron 设置脚本
# 用法: bash setup_cron.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_PATH=$(which python3)

echo "📅 设置每日科研简报 Cron 任务"
echo ""

# 添加 cron 任务（每天早上 8:00 运行）
CRON_CMD="0 8 * * * cd $SCRIPT_DIR && $PYTHON_PATH daily_report.py >> logs/daily_report.log 2>&1"

# 检查是否已存在
if crontab -l 2>/dev/null | grep -q "daily_report.py"; then
    echo "⚠️  Cron 任务已存在，跳过"
else
    # 创建日志目录
    mkdir -p $SCRIPT_DIR/logs

    # 添加到 crontab
    (crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -
    echo "✅ 已添加 Cron 任务: 每天 08:00 运行"
fi

echo ""
echo "📋 当前 Cron 任务列表:"
crontab -l 2>/dev/null | grep daily_report || echo "  (无)"

echo ""
echo "📝 其他常用命令:"
echo "  查看日志: tail -f $SCRIPT_DIR/logs/daily_report.log"
echo "  手动运行: cd $SCRIPT_DIR && python3 daily_report.py"
echo "  删除 Cron: crontab -e (删除对应行)"
