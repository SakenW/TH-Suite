# 已移除的V1兼容性路由 - 归档于 2025-09-16
# 这些路由已被统一的V1路由系统替代

# 移除的兼容性路由代码段：
# Lines 218-476 from main.py

compat_router_removed_code = '''
    # 兼容性端点
    from fastapi import APIRouter

    compat_router = APIRouter()

    @compat_router.get("/api/v1/scan-project-test-get")
    async def scan_project_test_get():
        """GET测试端点"""
        return {"success": True, "message": "GET test endpoint working"}

    @compat_router.post("/api/v1/scan-project-test")
    async def scan_project_test():
        """最简单的测试端点"""
        return {"success": True, "message": "test endpoint working"}

    @compat_router.post("/api/v1/scan-project-test-json")
    async def scan_project_test_json(request: dict):
        """测试JSON解析"""
        return {"success": True, "received": request}

    @compat_router.post("/api/v1/scan-project")
    async def scan_project_v1_compat(request: ScanRequest):
        """使用应用服务的扫描端点"""
        # ... 完整实现已移除

    @compat_router.get("/api/v1/scan-status/{scan_id}")
    async def get_scan_status_v1_compat(scan_id: str):
        """使用应用服务获取扫描状态"""
        # ... 完整实现已移除

    # ... 等等，所有 compat_router 相关代码

    @compat_router.get("/api/v1/scan-project-test-get")
    async def scan_project_test_get():
        """GET测试端点"""
        return {"success": True, "message": "GET test endpoint working"}

    @compat_router.post("/api/v1/scan-project-test")
    async def scan_project_test():
        """最简单的测试端点"""
        return {"success": True, "message": "test endpoint working"}

    @compat_router.post("/api/v1/scan-project-test-json")
    async def scan_project_test_json(request: dict):
        """测试JSON解析"""
        return {"success": True, "received": request}

    @compat_router.post("/api/v1/scan-project")
    async def scan_project_v1_compat(request: ScanRequest):
        """使用应用服务的扫描端点"""
        from application.services.scan_application_service import ScanApplicationService

        try:
            scan_service = ScanApplicationService()
            result = await scan_service.start_project_scan(
                directory=request.directory, incremental=request.incremental
            )

            if result["success"]:
                return {
                    "success": True,
                    "message": result["message"],
                    "job_id": result["scan_id"],
                    "scan_id": result["scan_id"],
                }
            else:
                raise HTTPException(
                    status_code=500, detail=result.get("message", "扫描启动失败")
                )

        except Exception as e:
            logger.error(f"启动扫描失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @compat_router.get("/api/v1/scan-status/{scan_id}")
    async def get_scan_status_v1_compat(scan_id: str):
        """使用应用服务获取扫描状态"""
        from application.services.scan_application_service import ScanApplicationService

        scan_service = ScanApplicationService()
        return await scan_service.get_scan_status(scan_id)

    @compat_router.get("/api/v1/scan-results/{scan_id}")
    async def get_scan_results_v1_compat(scan_id: str):
        """使用应用服务获取扫描结果"""
        from application.services.scan_application_service import ScanApplicationService

        scan_service = ScanApplicationService()
        return await scan_service.get_scan_results(scan_id)

    @compat_router.post("/api/v1/scan-cancel/{scan_id}")
    async def cancel_scan_v1_compat(scan_id: str):
        """使用应用服务取消扫描"""
        from application.services.scan_application_service import ScanApplicationService

        scan_service = ScanApplicationService()
        return await scan_service.cancel_scan(scan_id)

    @compat_router.get("/api/v1/scans/active")
    async def get_active_scans():
        """获取活跃的扫描状态"""
        try:
            active_scan_list = []
            for scan_id, scan_status in active_scans.items():
                active_scan_list.append(
                    {
                        "id": scan_id,
                        "status": scan_status.get("status", "unknown"),
                        "progress": scan_status.get("progress", 0),
                        "processed_files": scan_status.get("processed_files", 0),
                        "total_files": scan_status.get("total_files", 0),
                        "current_file": scan_status.get("current_file", ""),
                        "total_mods": scan_status.get("total_mods", 0),
                        "total_language_files": scan_status.get(
                            "total_language_files", 0
                        ),
                        "total_keys": scan_status.get("total_keys", 0),
                        "scan_mode": scan_status.get("scan_mode", "未知"),
                        "started_at": scan_status.get("started_at", ""),
                    }
                )

            return {"success": True, "data": active_scan_list}
        except Exception as e:
            logger.error(f"获取活跃扫描失败: {e}")
            return {"success": False, "error": str(e)}

    @compat_router.get("/api/v1/scans/history")
    async def get_scan_history():
        """获取历史扫描记录"""
        try:
            conn = sqlite3.connect("data/mc_l10n_v2_1.db")
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 从新的v2_1表结构获取扫描历史 (从packs表模拟scan_sessions)
            cursor.execute("""
                SELECT 
                    p.id,
                    p.path as project_path,
                    'completed' as status,
                    'filesystem' as scan_type,
                    COUNT(DISTINCT mr.mod_instance_id) as discovered_mods,
                    COUNT(DISTINCT ci.language_code) as discovered_languages,
                    COUNT(ci.id) as discovered_entries,
                    p.created_at as started_at,
                    p.updated_at as completed_at
                FROM packs p
                LEFT JOIN pack_versions pv ON p.id = pv.pack_version_id
                LEFT JOIN pack_mod_relations mr ON pv.id = mr.pack_version_id
                LEFT JOIN pack_content_relations cr ON pv.id = cr.pack_version_id
                LEFT JOIN content_instances ci ON cr.content_instance_id = ci.id
                WHERE p.is_active = 1
                GROUP BY p.id, p.path, p.created_at, p.updated_at
                ORDER BY p.updated_at DESC
                LIMIT 50
            """)
            sessions = cursor.fetchall()

            scan_list = []
            for session in sessions:
                scan_list.append(
                    {
                        "id": session["id"],
                        "directory": session["project_path"],
                        "status": session["status"],
                        "scan_type": session["scan_type"],
                        "total_mods": session["discovered_mods"] or 0,
                        "total_language_files": session["discovered_languages"] or 0,
                        "total_keys": session["discovered_entries"] or 0,
                        "started_at": session["started_at"],
                        "completed_at": session["completed_at"],
                    }
                )

            conn.close()
            return {"success": True, "data": scan_list}

        except Exception as e:
            logger.error(f"获取历史扫描记录失败: {e}")
            return {"success": False, "error": str(e)}

    @compat_router.get("/api/v1/scans/latest")
    async def get_latest_scan():
        """获取最新的扫描结果"""
        try:
            conn = sqlite3.connect("data/mc_l10n_v2_1.db")
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 获取最新完成的扫描
            cursor.execute("""
                SELECT * FROM scan_sessions
                WHERE status = 'completed'
                ORDER BY completed_at DESC
                LIMIT 1
            """)
            session = cursor.fetchone()

            if not session:
                conn.close()
                return {"success": True, "data": None}

            scan_id = session["id"]

            # 获取V6架构的模组数据
            cursor.execute(
                """
                SELECT uid, modid, name, created_at, updated_at FROM core_mods
                ORDER BY name
            """
            )
            mods = cursor.fetchall()

            mod_list = []
            for mod in mods:
                # 获取该模组的语言文件统计 - V6架构
                cursor.execute(
                    """
                    SELECT COUNT(lf.uid) as lang_count, COUNT(te.uid) as total_keys
                    FROM core_language_files lf
                    LEFT JOIN core_translation_entries te ON lf.uid = te.language_file_uid
                    WHERE lf.carrier_uid = ?
                """,
                    (mod["uid"],),
                )
                stats = cursor.fetchone()
                
                # 获取该模组的版本信息
                cursor.execute(
                    """
                    SELECT version, loader, mc_version FROM core_mod_versions
                    WHERE mod_uid = ?
                    ORDER BY discovered_at DESC LIMIT 1
                """,
                    (mod["uid"],),
                )
                version_info = cursor.fetchone()

                mod_list.append(
                    {
                        "id": mod["modid"],
                        "name": mod["name"],
                        "version": version_info["version"] if version_info else "",
                        "file_path": "",  # V6架构不存储文件路径
                        "mod_loader": version_info["loader"] if version_info else "",
                        "language_files": stats["lang_count"] if stats else 0,
                        "total_keys": stats["total_keys"] if stats else 0,
                    }
                )

            conn.close()

            # 解析 metadata JSON 字段以获取真实的统计数据
            import json

            metadata = {}
            if session["metadata"]:
                try:
                    metadata = json.loads(session["metadata"])
                except json.JSONDecodeError:
                    pass

            return {
                "success": True,
                "data": {
                    "scan_id": scan_id,
                    "directory": session["project_path"],
                    "completed_at": session["completed_at"],
                    "statistics": {
                        "total_mods": metadata.get(
                            "total_mods", session["discovered_mods"]
                        ),
                        "total_language_files": metadata.get(
                            "total_language_files", session["discovered_languages"]
                        ),
                        "total_keys": metadata.get(
                            "total_keys", session["discovered_entries"]
                        ),
                    },
                    "mods": mod_list,
                },
            }

        except Exception as e:
            logger.error(f"获取最新扫描结果失败: {e}")
            return {"success": False, "error": str(e)}

    app.include_router(compat_router)

    # 直接在app上添加测试路由
    @app.get("/api/v1/direct-test")
    async def direct_test():
        return {"success": True, "message": "Direct route working"}
'''

# 移除位置：main.py 第217-478行（包含所有兼容性路由定义）
# 移除日期：2025-09-16
# 说明：这些路由已经被 api/routes/ 下的统一路由系统替代
# 新系统使用更清晰的 /api/v1/ 前缀，不再需要兼容性层