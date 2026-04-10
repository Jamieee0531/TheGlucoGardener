# 测试数据库连接

在 ECS 上运行：

```bash
python3 -c "
import psycopg2, os
from dotenv import load_dotenv
load_dotenv()
conn = psycopg2.connect(host=os.getenv('PG_HOST'), port=os.getenv('PG_PORT'), user=os.getenv('PG_USER'), password=os.getenv('PG_PASSWORD'), dbname=os.getenv('PG_DB'))
print('DB连接成功!')
cur = conn.cursor()
cur.execute('SELECT count(*) FROM information_schema.tables')
print(f'表数量: {cur.fetchone()[0]}')
conn.close()
"
```
