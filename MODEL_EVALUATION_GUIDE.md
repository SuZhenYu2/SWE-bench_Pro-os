# 模型测评完整指南

本指南说明如何使用集成的 mini-swe-agent 进行端到端的模型测评。

## 🎯 系统架构

```
数据输入 (instances.csv)
    ↓
multi_model_evaluator.py
    ↓
mini-swe-agent (生成 patch)
    ↓
swe_bench_pro_eval.py (评估 patch)
    ↓
评估报告 (evaluation_report.md)
```

## 📋 前置条件

### 1. 激活虚拟环境
```bash
cd /home/ubuntu/data/swe/SWE-bench_Pro-os
source venv/bin/activate
```

### 2. 设置 API Keys

```bash
# Anthropic (for Claude models)
export ANTHROPIC_API_KEY="your_anthropic_key_here"

# OpenAI (for Qwen/GPT models)
export OPENAI_API_KEY="your_openai_key_here"
export OPENAI_API_BASE="https://api.openai.com/v1"  # 或 Qwen API endpoint
```

### 3. 验证配置

```bash
# 测试 mini-swe-agent
mini-swe-agent --help

# 验证 API keys
echo $ANTHROPIC_API_KEY
echo $OPENAI_API_KEY
```

---

## 🚀 使用方法

### 方法 1：单模型测评

```bash
source venv/bin/activate

# 测试 Claude Opus 4.7
python3 multi_model_evaluator.py \
  --model opus --runs 5 \
  --input-dir test_data \
  --output-dir results/opus_eval_$(date +%Y%m%d)

# 测试 Qwen 3.6 Plus
python3 multi_model_evaluator.py \
  --model qwen --runs 5 \
  --input-dir test_data \
  --output-dir results/qwen_eval_$(date +%Y%m%d)
```

### 方法 2：多模型对比测评

```bash
# Claude vs Qwen 对比
python3 multi_model_evaluator.py \
  --model opus --runs 10 \
  --model sonnet --runs 15 \
  --model qwen --runs 10 \
  --input-dir test_data \
  --output-dir results/multi_model_$(date +%Y%m%d) \
  --threshold "opus:>=7,sonnet:>=10,qwen:>=7"
```

### 方法 3：生成对比报告

```bash
# 仅生成报告（不重新评估）
python3 multi_model_evaluator.py \
  --report \
  --input-dir results/multi_model_20260611
```

---

## 📊 支持的模型

### Claude 系列

| 模型标识 | 名称 | API 模型 ID | Max Tokens |
|---------|------|-------------|------------|
| `opus` | Claude Opus 4.7 | claude-opus-4-7 | 8192 |
| `sonnet` | Claude Sonnet 4.6 | claude-sonnet-4-6 | 8192 |
| `haiku` | Claude Haiku 4.5 | claude-haiku-4-5-20251001 | 8192 |

### Qwen 系列

| 模型标识 | 名称 | API 模型 ID | Max Tokens |
|---------|------|-------------|------------|
| `qwen` | Qwen 3.6 Plus | qwen3.6-plus | 32768 |
| `qwen-plus` | Qwen Plus | qwen-plus | 8192 |
| `qwen-turbo` | Qwen Turbo | qwen-turbo | 8192 |
| `qwen-max` | Qwen Max | qwen-max | 8192 |

### GPT 系列

| 模型标识 | 名称 | API 模型 ID | Max Tokens |
|---------|------|-------------|------------|
| `gpt4` | GPT-4 | gpt-4 | 8192 |
| `gpt4-turbo` | GPT-4 Turbo | gpt-4-turbo | 8192 |

---

## 🔧 高级配置

### 自定义超时时间

编辑 `multi_model_evaluator.py` 中的超时设置：

```python
# 第 257 行附近
timeout=300  # 改为你想要的秒数
```

### 自定义成本限制

```python
# 第 253 行附近
"--cost-limit", "10.0"  # 改为你的成本上限（美元）
```

### 添加新模型

编辑 `MODEL_CONFIGS` 字典：

```python
MODEL_CONFIGS = {
    "your-model": {
        "name": "Your Model Name",
        "api_type": "anthropic",  # or "openai"
        "model_name": "model-id",
        "temperature": 0.2,
        "max_tokens": 8192,
    },
    # ... 其他模型
}
```

---

## 📁 输出结构

```
output_dir/
├── evaluation_report.md          # 总报告
├── opus/
│   ├── run_1/
│   │   ├── instance_test_1.jsonl
│   │   ├── instance_test_2.jsonl
│   │   └── instance_test_3.jsonl
│   └── run_2/
│       └── ...
├── qwen/
│   └── run_1/
│       └── ...
└── sonnet/
    └── run_1/
        └── ...
```

---

## 🐛 故障排除

### 问题 1: "ANTHROPIC_API_KEY not set"

**解决方案：**
```bash
export ANTHROPIC_API_KEY="your_key"
# 或在 ~/.bashrc 中添加
echo 'export ANTHROPIC_API_KEY="your_key"' >> ~/.bashrc
source ~/.bashrc
```

### 问题 2: mini-swe-agent 超时

**解决方案：**
- 增加超时时间（见高级配置）
- 简化测试实例
- 检查网络连接

### 问题 3: API 限流

**解决方案：**
- 减少并发数（`--runs` 参数）
- 增加请求间隔
- 使用多个 API key 轮换

### 问题 4: 模型返回错误

**解决方案：**
```bash
# 查看详细日志
python3 multi_model_evaluator.py --model opus --runs 1 --input-dir test_data 2>&1 | tee debug.log

# 检查生成的输出文件
cat results/opus/run_1/instance_test_1.jsonl
```

---

## 📈 最佳实践

### 1. 小规模测试

先用少量实例测试：
```bash
python3 multi_model_evaluator.py \
  --model opus --runs 1 \
  --input-dir test_data \
  --output-dir test_run
```

### 2. 逐步扩展

确认正常后再增加规模：
```bash
# 2 轮次
python3 multi_model_evaluator.py --model opus --runs 2 ...

# 5 轮次
python3 multi_model_evaluator.py --model opus --runs 5 ...

# 完整评估
python3 multi_model_evaluator.py --model opus --runs 10 ...
```

### 3. 监控成本

- 设置合理的 `--cost-limit`
- 从便宜的模型开始（haiku, qwen-turbo）
- 监控 API 使用情况

### 4. 保存结果

```bash
# 使用时间戳命名
OUTPUT_DIR="results/eval_$(date +%Y%m%d_%H%M%S)"

python3 multi_model_evaluator.py \
  --model opus --runs 5 \
  --output-dir $OUTPUT_DIR

# 备份结果
cp -r $OUTPUT_DIR $OUTPUT_DIR.backup
```

---

## 🎯 完整示例

```bash
#!/bin/bash
# complete_eval.sh - 完整的模型测评脚本

set -e

# 1. 设置环境
cd /home/ubuntu/data/swe/SWE-bench_Pro-os
source venv/bin/activate

# 2. 设置 API keys
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."

# 3. 创建输出目录
OUTPUT_DIR="results/eval_$(date +%Y%m%d_%H%M%S)"
mkdir -p $OUTPUT_DIR

# 4. 运行评估
echo "🚀 开始多模型评估..."
python3 multi_model_evaluator.py \
  --model opus --runs 5 \
  --model sonnet --runs 8 \
  --model qwen --runs 5 \
  --input-dir test_data \
  --output-dir $OUTPUT_DIR \
  --threshold "opus:>=3,sonnet:>=5,qwen:>=3" \
  2>&1 | tee $OUTPUT_DIR/eval.log

# 5. 查看报告
echo "📊 评估完成！"
cat $OUTPUT_DIR/evaluation_report.md
```

使用：
```bash
chmod +x complete_eval.sh
./complete_eval.sh
```

---

## 📚 参考资料

- [mini-swe-agent 文档](https://mini-swe-agent.com/latest/)
- [SWE-bench 排行榜](https://swebench.com/)
- [Claude API 文档](https://docs.anthropic.com/)
- [Qwen API 文档](https://help.aliyun.com/zh/dashscope/)

---

## 🆘 获取帮助

如有问题，请查看：
1. 本文档的故障排除部分
2. mini-swe-agent 文档
3. 检查日志文件
4. 验证 API keys 和网络连接
