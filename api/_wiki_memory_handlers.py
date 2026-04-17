
 # ── Wiki/Memory Browser (POST) ──
 def _handle_wiki_memory_post(handler, body, path):
     """Handle all wiki/memory POST operations."""
     from api.wiki_memory_api import (
         list_wiki_pages, get_wiki_page, create_wiki_page, update_wiki_page, delete_wiki_page,
         search_wiki_pages, get_wiki_categories, get_wiki_tags,
         list_memster_memories, get_memster_memory_by_id, create_memster_memory,
         update_memster_memory, delete_memster_memory, search_memster_memories,
         get_memster_categories, get_memster_tags, get_related_memories,
         get_memster_briefing, run_memster_hybrid_search, add_memory_tag,
         remove_memory_tag, get_health_stats, get_sp_members, get_sp_status, get_sp_activity_timeline
     )
     
     try:
         if path == "/api/wiki/pages":
             category = body.get("category", "all")
             limit = body.get("limit", 50)
             result = list_wiki_pages(category=category, limit=int(limit))
             return j(handler, result)
         
         if path == "/api/wiki/page":
             slug = body.get("slug")
             if not slug:
                 return bad(handler, "slug is required")
             result = get_wiki_page(slug)
             return j(handler, result)
         
         if path == "/api/wiki/create":
             require(body, ["slug", "title", "category", "content"])
             result = create_wiki_page(
                 body["slug"],
                 body["title"],
                 body["category"],
                 body["content"],
                 body.get("tags"),
                 body.get("sources")
             )
             return j(handler, result)
         
         if path == "/api/wiki/update":
             require(body, "slug")
             result = update_wiki_page(
                 body["slug"],
                 body.get("title"),
                 body.get("category"),
                 body.get("content"),
                 body.get("tags"),
                 body.get("sources")
             )
             return j(handler, result)
         
         if path == "/api/wiki/delete":
             require(body, "slug")
             result = delete_wiki_page(body["slug"])
             return j(handler, result)
         
         if path == "/api/wiki/search":
             require(body, "query")
             limit = body.get("limit", 10)
             result = search_wiki_pages(body["query"], limit=int(limit))
             return j(handler, result)
         
         if path == "/api/wiki/categories":
             result = get_wiki_categories()
             return j(handler, result)
         
         if path == "/api/wiki/tags":
             result = get_wiki_tags()
             return j(handler, result)
         
         # Memories
         if path == "/api/memory/list":
             result = list_memster_memories(
                 category=body.get("category"),
                 tier=body.get("tier"),
                 limit=body.get("limit", 50),
                 offset=body.get("offset", 0),
                 search=body.get("search")
             )
             return j(handler, result)
         
         if path == "/api/memory/get":
             require(body, "id")
             result = get_memster_memory_by_id(body["id"])
             return j(handler, result)
         
         if path == "/api/memory/create":
             require(body, "content")
             result = create_memster_memory(
                 body["content"],
                 body.get("category", "observation"),
                 body.get("tier", "L2"),
                 body.get("tags")
             )
             return j(handler, result)
         
         if path == "/api/memory/update":
             require(body, "id")
             result = update_memster_memory(
                 body["id"],
                 body.get("content"),
                 body.get("category"),
                 body.get("tier"),
                 body.get("tags")
             )
             return j(handler, result)
         
         if path == "/api/memory/delete":
             require(body, "id")
             result = delete_memster_memory(body["id"])
             return j(handler, result)
         
         if path == "/api/memory/search":
             require(body, "query")
             result = search_memster_memories(body["query"], body.get("limit", 20))
             return j(handler, result)
         
         if path == "/api/memory/hybrid":
             require(body, "query")
             result = run_memster_hybrid_search(body["query"], body.get("limit", 10))
             return j(handler, result)
         
         if path == "/api/memory/related":
             require(body, "id")
             result = get_related_memories(body["id"], body.get("limit", 10))
             return j(handler, result)
         
         if path == "/api/memory/categories":
             result = get_memster_categories()
             return j(handler, result)
         
         if path == "/api/memory/tags":
             result = get_memster_tags()
             return j(handler, result)
         
         if path == "/api/memory/add-tag":
             require(body, ["id", "tag"])
             result = add_memory_tag(body["id"], body["tag"])
             return j(handler, result)
         
         if path == "/api/memory/remove-tag":
             require(body, ["id", "tag"])
             result = remove_memory_tag(body["id"], body["tag"])
             return j(handler, result)
         
         if path == "/api/memory/briefing":
             result = get_memster_briefing()
             return j(handler, result)
         
         # SP Headmates
         if path == "/api/sp/members":
             result = get_sp_members(body.get("include_archived", False))
             return j(handler, result)
         
         if path == "/api/sp/status":
             result = get_sp_status()
             return j(handler, result)
         
         if path == "/api/sp/timeline":
             hours = body.get("hours", 24)
             result = get_sp_activity_timeline(int(hours))
             return j(handler, result)
         
         # Health check
         if path == "/api/wiki-memory/health":
             result = get_health_stats()
             return j(handler, result)
         
         return None  # Not handled
     except ValueError as e:
         return bad(handler, str(e))
     except Exception as e:
         logger.exception("Wiki/memory POST handler failed")
         return j(handler, {"error": str(e)}, status=500)
 
 # Add wiki/memory routes
 if parsed.path.startswith("/api/wiki/") or parsed.path.startswith("/api/memory/") or parsed.path.startswith("/api/sp/"):
     result = _handle_wiki_memory_post(handler, body, parsed.path)
     if result is not None:
         return result

