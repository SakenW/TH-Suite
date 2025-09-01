PRAGMA foreign_keys=ON;
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;

-- 0) 基础枚举（用 CHECK 约束代替）
-- 状态：drafted/validated/mapped/queued/submitted/synced/conflict/rejected
-- 方向：push(本地->服务器) / pull(服务器->本地)

----------------------------------------------------------------------
-- 1) 原始内容：本地“所见即所得”的详细记录（未转换前）
----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS local_entries (
  local_id            INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id          TEXT NOT NULL,                           -- 固定 "minecraft"（仍保留字段以兼容未来）
  source_type         TEXT NOT NULL,                           -- mod|pack|openloader|kubejs|ct|datapack|patchouli|quest|external
  source_file         TEXT NOT NULL,                           -- 相对路径（jar 内或 overrides 相对）
  source_locator      TEXT,                                    -- 细粒度定位：JSONPath/键路径/资源标识符
  source_lang_bcp47   TEXT,                                    -- 如 zh-CN / en-US（可为空，表示源语未知）
  source_context_json TEXT NOT NULL,                           -- JSON：上下文（周边文本/注释/截图引用等）
  source_payload_json TEXT NOT NULL,                           -- JSON：原始文本/结构（未转换）
  note                TEXT,                                    -- 备注
  created_at          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_local_entries_proj ON local_entries(project_id);
CREATE INDEX IF NOT EXISTS ix_local_entries_src ON local_entries(source_type, source_file);

----------------------------------------------------------------------
-- 2) 拟合/映射：把 local → server UIDA（可反复试算/校验）
----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mapping_plan (
  plan_id             INTEGER PRIMARY KEY AUTOINCREMENT,
  local_id            INTEGER NOT NULL REFERENCES local_entries(local_id) ON DELETE CASCADE,
  proposed_namespace  TEXT NOT NULL,                           -- 拟合的 server 端 namespace（如 game.minecraft.mod.item.name）
  proposed_keys_json  TEXT NOT NULL,                           -- 拟合的 keys 原文（未哈希）
  keyhash_hex_local   TEXT,                                    -- 本地试算哈希（排序 JSON 近似，最终以服务器为准）
  lang_mc             TEXT,                                    -- 目标 MC 语言码（如 zh_cn）
  validation_state    TEXT NOT NULL DEFAULT 'drafted' CHECK (validation_state IN ('drafted','validated','mapped')),
  validation_errors   TEXT,                                    -- JSON 数组，记录校验器输出
  created_at          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(local_id, proposed_namespace, proposed_keys_json, lang_mc) -- 防重复同方案
);

CREATE INDEX IF NOT EXISTS ix_mapping_state ON mapping_plan(validation_state);

----------------------------------------------------------------------
-- 3) 提交队列：将通过校验的映射打包提交（push）
----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS outbound_queue (
  queue_id            INTEGER PRIMARY KEY AUTOINCREMENT,
  plan_id             INTEGER NOT NULL REFERENCES mapping_plan(plan_id) ON DELETE CASCADE,
  intent              TEXT NOT NULL CHECK (intent IN ('upsert','delete')),
  submit_payload_json TEXT NOT NULL,                           -- 发送给服务器的最小提交体（lang/payload/元）
  base_etag           TEXT,                                    -- 乐观并发控制：编辑基线
  queue_state         TEXT NOT NULL DEFAULT 'queued' CHECK (queue_state IN ('queued','submitted','accepted','rejected','conflict','error')),
  result_message      TEXT,                                    -- 返回信息/错误详情
  server_content_id   TEXT,                                    -- 服务器生成/命中的内容行ID
  submitted_at        TEXT,
  updated_at          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_outbound_state ON outbound_queue(queue_state);

----------------------------------------------------------------------
-- 4) 回写快照：服务器导出的全量/增量（pull）
----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS inbound_snapshot (
  snapshot_id         TEXT PRIMARY KEY,                        -- 服务端快照ID
  obtained_at         TEXT NOT NULL,                           -- 拉取时间
  project_id          TEXT NOT NULL,
  from_snapshot_id    TEXT                                     -- 增量来源（可空，全量为 NULL）
);

CREATE TABLE IF NOT EXISTS inbound_items (
  snapshot_id         TEXT NOT NULL REFERENCES inbound_snapshot(snapshot_id) ON DELETE CASCADE,
  server_content_id   TEXT NOT NULL,                           -- 服务端行ID
  namespace           TEXT NOT NULL,
  keys_sha256_hex     TEXT NOT NULL,                           -- 服务端权威哈希（hex）
  lang_mc             TEXT NOT NULL,                           -- zh_cn/en_us...
  server_payload_json TEXT NOT NULL,                           -- 服务器存量的 payload（往返后要还原为 local 表达）
  etag                TEXT,
  updated_at          TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_inbound_item ON inbound_items(snapshot_id, server_content_id);

----------------------------------------------------------------------
-- 5) 双向映射登记：local_id ↔ server_content_id（多版本回溯）
----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mapping_link (
  link_id             INTEGER PRIMARY KEY AUTOINCREMENT,
  local_id            INTEGER NOT NULL REFERENCES local_entries(local_id) ON DELETE CASCADE,
  plan_id             INTEGER REFERENCES mapping_plan(plan_id) ON DELETE SET NULL,
  server_content_id   TEXT NOT NULL,
  namespace           TEXT NOT NULL,
  keys_sha256_hex     TEXT NOT NULL,
  lang_mc             TEXT NOT NULL,
  last_seen_snapshot  TEXT,                                    -- 最近一次看到它的 snapshot_id
  created_at          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(local_id, server_content_id, lang_mc)
);

----------------------------------------------------------------------
-- 6) 校验/审计
----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_log (
  id                  INTEGER PRIMARY KEY AUTOINCREMENT,
  ts                  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  actor               TEXT NOT NULL,                           -- user/tool
  action              TEXT NOT NULL,                           -- map.validate / map.apply / push.submit / pull.merge ...
  local_id            INTEGER,
  plan_id             INTEGER,
  queue_id            INTEGER,
  server_content_id   TEXT,
  detail_json         TEXT                                      -- 任意细节
);

-- 自动更新 updated_at 字段的触发器
CREATE TRIGGER IF NOT EXISTS tr_local_entries_updated_at
  AFTER UPDATE ON local_entries
  FOR EACH ROW
  WHEN NEW.updated_at = OLD.updated_at
BEGIN
  UPDATE local_entries SET updated_at = CURRENT_TIMESTAMP WHERE local_id = NEW.local_id;
END;

CREATE TRIGGER IF NOT EXISTS tr_mapping_plan_updated_at
  AFTER UPDATE ON mapping_plan
  FOR EACH ROW
  WHEN NEW.updated_at = OLD.updated_at
BEGIN
  UPDATE mapping_plan SET updated_at = CURRENT_TIMESTAMP WHERE plan_id = NEW.plan_id;
END;

CREATE TRIGGER IF NOT EXISTS tr_outbound_queue_updated_at
  AFTER UPDATE ON outbound_queue
  FOR EACH ROW
  WHEN NEW.updated_at = OLD.updated_at
BEGIN
  UPDATE outbound_queue SET updated_at = CURRENT_TIMESTAMP WHERE queue_id = NEW.queue_id;
END;

-- 常用视图：需要什么再加
CREATE VIEW IF NOT EXISTS v_ready_to_queue AS
SELECT p.plan_id, p.local_id, p.proposed_namespace, p.proposed_keys_json, p.lang_mc
FROM mapping_plan p
LEFT JOIN outbound_queue q ON q.plan_id = p.plan_id AND q.queue_state IN ('queued','submitted')
WHERE p.validation_state='mapped' AND q.queue_id IS NULL;

-- 额外的复合索引优化
CREATE INDEX IF NOT EXISTS ix_mapping_link_server ON mapping_link(server_content_id, lang_mc);
CREATE INDEX IF NOT EXISTS ix_inbound_items_content ON inbound_items(server_content_id, lang_mc);
CREATE INDEX IF NOT EXISTS ix_audit_log_actor_action ON audit_log(actor, action, ts);
