# 城市就业与生活成本分析 Streamlit 应用

## 运行方式

在项目根目录执行：

```powershell
pip install -r streamlit_app/requirements.txt
streamlit run streamlit_app/app.py
```

## DeepSeek API 配置

如果需要启用智能分析，请设置环境变量：

```powershell
$env:DEEPSEEK_API_KEY="你的 DeepSeek API Key"
```

然后重新运行：

```powershell
streamlit run streamlit_app/app.py
```

如果不设置 API Key，应用仍然可以正常展示仪表盘，只是“智能分析”模块会提示未配置。

## 文件说明

| 文件 | 作用 |
| --- | --- |
| `app.py` | Streamlit 主程序 |
| `data_loader.py` | 数据读取、筛选和指标计算 |
| `charts.py` | 图表绘制函数 |
| `deepseek_client.py` | DeepSeek API 调用 |
| `styles.py` | 页面样式 |
| `requirements.txt` | 运行依赖 |
