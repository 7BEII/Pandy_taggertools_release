# 配置文件说明

## 文件结构

### apikey.json（API配置文件）⭐
**用途**：存储API密钥和激活信息（敏感信息）

**包含内容**：
- `providers` - API提供商配置（SiliconFlow、ModelScope、Tuzi等）
  - `api_key` - API密钥（敏感）
  - `base_url` - API地址
  - `models` - 可用模型列表
  - `hiddenModels` - 隐藏的模型列表
- `current_provider` - 当前使用的API提供商
- `model` - 当前使用的模型
- `license_code` - 软件激活码（敏感）
- `ai_analysis_prompt` - AI分析提示词

### config.json（提示词模板配置）⭐
**用途**：存储用户自定义的提示词模板

**包含内容**：
- `prompt_templates` - 提示词模板
  - `tagging` - 单图反推模板
    - `selected` - 当前选中的模板ID
    - `templates` - 模板列表
  - `editing` - 图像编辑模板
    - `selected` - 当前选中的模板ID
    - `templates` - 模板列表

### 其他模板文件
- `默认单图反推.json` - 默认单图反推提示词模板
- `默认编辑模型.json` - 默认编辑模型提示词模板

## 为什么使用两个配置文件？

### 设计理由
1. **安全性分离**：
   - `apikey.json` 包含敏感信息（API密钥、激活码）
   - `config.json` 只包含提示词模板（非敏感）
   - 便于备份时区分敏感和非敏感数据

2. **功能分离**：
   - API配置相对固定，不常修改
   - 提示词模板经常修改和切换
   - 分开存储避免互相干扰

3. **易于管理**：
   - 可以单独备份/分享提示词模板
   - 不会泄露API密钥

## 配置简化历史

**之前的设计**（已优化）：
- `apikey.json` - API配置
- `jihuoma.json` - 激活码 ❌ 已删除
- `license.key` - 激活密钥 ❌ 已删除
- `config.json` - 提示词模板
- `config.example.json` - 示例配置 ❌ 已删除

**现在的设计**（简化后）：
- `apikey.json` - API配置 + 激活码（敏感信息）✅
- `config.json` - 提示词模板（用户数据）✅

**优势**：
- ✅ 减少文件数量，从5个减少到2个
- ✅ 配置集中管理，更易维护
- ✅ 避免配置分散导致的混乱
- ✅ 激活码与API配置统一存储，逻辑更清晰
- ✅ 敏感信息和用户数据分离，更安全

## 使用建议

### 备份配置
```bash
# 备份敏感信息（不要分享）
备份 apikey.json

# 备份提示词模板（可以分享）
备份 config.json
```

### 分享模板
如果你想分享自己的提示词模板给其他用户：
1. 只需分享 `config.json` 文件
2. 不要分享 `apikey.json`（包含你的API密钥）

### 重置配置
- 删除 `apikey.json` - 重置API配置和激活信息
- 删除 `config.json` - 重置提示词模板（会恢复默认）

## 注意事项

1. **不要手动编辑 apikey.json**，除非你知道自己在做什么
2. **激活码格式**：20位字符（16位十六进制 + "PDYY"后缀）
3. **备份重要**：修改配置前建议备份这两个文件
4. **不要泄露**：apikey.json 包含敏感信息，不要上传到公开位置
