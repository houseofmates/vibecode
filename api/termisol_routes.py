"""
API Routes for Termisol Terminal Integration
Replaces the basic terminal API routes with advanced Termisol features
"""
import asyncio
import json
import logging
from typing import Dict, Any
from aiohttp import web, WSMsgType
from .termisol_adapter import (
    create_termisol_session, 
    get_termisol_session, 
    list_termisol_sessions, 
    close_termisol_session
)

logger = logging.getLogger(__name__)

async def create_termisol_terminal(request: web.Request) -> web.Response:
    """Create a new Termisol terminal session"""
    try:
        data = await request.json()
        cwd = data.get('cwd')
        session_id = data.get('session_id', 'anonymous')
        features = data.get('features', {})
        
        # Create Termisol session
        session = create_termisol_session(cwd, features, session_id)
        
        return web.json_response({
            'terminal_id': session.terminal_id,
            'name': session.name,
            'cwd': session.cwd,
            'features': session.features,
            'connected': session.connected
        })
    except Exception as e:
        logger.error(f"Failed to create Termisol terminal: {e}")
        return web.json_response(
            {'error': f'Failed to create terminal: {str(e)}'}, 
            status=500
        )

async def list_termisol_terminals(request: web.Request) -> web.Response:
    """List all Termisol terminal sessions"""
    try:
        session_id = request.query.get('session_id')
        terminals = list_termisol_sessions(session_id)
        
        return web.json_response({
            'terminals': terminals,
            'total': len(terminals)
        })
    except Exception as e:
        logger.error(f"Failed to list terminals: {e}")
        return web.json_response(
            {'error': f'Failed to list terminals: {str(e)}'}, 
            status=500
        )

async def get_termisol_terminal_info(request: web.Request) -> web.Response:
    """Get detailed information about a Termisol terminal"""
    try:
        terminal_id = request.match_info['terminal_id']
        session = get_termisol_session(terminal_id)
        
        if not session:
            return web.json_response(
                {'error': 'Terminal not found'}, 
                status=404
            )
        
        return web.json_response({
            'terminal_id': session.terminal_id,
            'name': session.name,
            'cwd': session.cwd,
            'created_at': session.created_at,
            'session_id': session.session_id,
            'features': session.features,
            'connected': session.connected,
            'available_features': [
                {
                    'name': f.name,
                    'enabled': f.enabled,
                    'description': f.description,
                    'category': f.category
                }
                for f in session.get_features()
            ]
        })
    except Exception as e:
        logger.error(f"Failed to get terminal info: {e}")
        return web.json_response(
            {'error': f'Failed to get terminal info: {str(e)}'}, 
            status=500
        )

async def write_to_termisol_terminal(request: web.Request) -> web.Response:
    """Write input to a Termisol terminal"""
    try:
        terminal_id = request.match_info['terminal_id']
        data = await request.json()
        input_data = data.get('data', '')
        
        session = get_termisol_session(terminal_id)
        if not session:
            return web.json_response(
                {'error': 'Terminal not found'}, 
                status=404
            )
        
        success = await session.write(input_data)
        if success:
            return web.json_response({'success': True})
        else:
            return web.json_response(
                {'error': 'Failed to write to terminal'}, 
                status=500
            )
    except Exception as e:
        logger.error(f"Failed to write to terminal: {e}")
        return web.json_response(
            {'error': f'Failed to write to terminal: {str(e)}'}, 
            status=500
        )

async def resize_termisol_terminal(request: web.Request) -> web.Response:
    """Resize a Termisol terminal"""
    try:
        terminal_id = request.match_info['terminal_id']
        data = await request.json()
        cols = data.get('cols', 80)
        rows = data.get('rows', 24)
        
        session = get_termisol_session(terminal_id)
        if not session:
            return web.json_response(
                {'error': 'Terminal not found'}, 
                status=404
            )
        
        await session.resize(cols, rows)
        return web.json_response({'success': True})
    except Exception as e:
        logger.error(f"Failed to resize terminal: {e}")
        return web.json_response(
            {'error': f'Failed to resize terminal: {str(e)}'}, 
            status=500
        )

async def close_termisol_terminal(request: web.Request) -> web.Response:
    """Close a Termisol terminal session"""
    try:
        terminal_id = request.match_info['terminal_id']
        success = close_termisol_session(terminal_id)
        
        if success:
            return web.json_response({'success': True})
        else:
            return web.json_response(
                {'error': 'Terminal not found'}, 
                status=404
            )
    except Exception as e:
        logger.error(f"Failed to close terminal: {e}")
        return web.json_response(
            {'error': f'Failed to close terminal: {str(e)}'}, 
            status=500
        )

async def update_terminal_features(request: web.Request) -> web.Response:
    """Update terminal features"""
    try:
        terminal_id = request.match_info['terminal_id']
        data = await request.json()
        feature_updates = data.get('features', {})
        
        session = get_termisol_session(terminal_id)
        if not session:
            return web.json_response(
                {'error': 'Terminal not found'}, 
                status=404
            )
        
        # Update features
        for feature, enabled in feature_updates.items():
            session.enable_feature(feature, enabled)
        
        return web.json_response({
            'success': True,
            'features': session.features
        })
    except Exception as e:
        logger.error(f"Failed to update features: {e}")
        return web.json_response(
            {'error': f'Failed to update features: {str(e)}'}, 
            status=500
        )

async def stream_termisol_output(request: web.Request) -> web.Response:
    """Stream terminal output via Server-Sent Events (SSE)"""
    try:
        terminal_id = request.match_info['terminal_id']
        client_id = request.query.get('client_id', f'client_{int(asyncio.get_event_loop().time())}')
        
        session = get_termisol_session(terminal_id)
        if not session:
            return web.json_response(
                {'error': 'Terminal not found'}, 
                status=404
            )
        
        # Add client to session
        session.add_client(client_id)
        
        # Create SSE response
        response = web.StreamResponse(
            status=200,
            reason='OK',
            headers={
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Cache-Control'
            }
        )
        
        await response.prepare(request)
        
        # Send initial ready event
        await response.write(f'event: ready\ndata: {json.dumps({"terminal_id": terminal_id, "name": session.name})}\n\n'.encode())
        
        # Stream output
        try:
            while True:
                output = await session.get_output(timeout=1.0)
                if output:
                    await response.write(f'event: {output["type"]}\ndata: {json.dumps(output)}\n\n'.encode())
                
                # Send periodic heartbeat
                if int(asyncio.get_event_loop().time()) % 10 == 0:
                    await response.write('event: heartbeat\n\n'.encode())
                    
        except (asyncio.CancelledError, ConnectionResetError):
            pass
        finally:
            # Remove client from session
            session.remove_client(client_id)
        
        return response
    except Exception as e:
        logger.error(f"Failed to stream output: {e}")
        return web.json_response(
            {'error': f'Failed to stream output: {str(e)}'}, 
            status=500
        )

async def termisol_websocket_handler(request: web.Request) -> web.WebSocketResponse:
    """WebSocket handler for real-time terminal communication"""
    try:
        terminal_id = request.match_info['terminal_id']
        session = get_termisol_session(terminal_id)
        
        if not session:
            return web.json_response(
                {'error': 'Terminal not found'}, 
                status=404
            )
        
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        # Add WebSocket client
        client_id = f'ws_{int(asyncio.get_event_loop().time())}'
        session.add_client(client_id)
        
        # Send initial connection message
        await ws.send_str(json.dumps({
            'type': 'connected',
            'terminal_id': terminal_id,
            'name': session.name,
            'features': session.features
        }))
        
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        msg_type = data.get('type')
                        
                        if msg_type == 'input':
                            await session.write(data.get('data', ''))
                        elif msg_type == 'resize':
                            cols = data.get('cols', 80)
                            rows = data.get('rows', 24)
                            await session.resize(cols, rows)
                        elif msg_type == 'feature_update':
                            feature = data.get('feature')
                            enabled = data.get('enabled', True)
                            session.enable_feature(feature, enabled)
                        elif msg_type == 'ping':
                            await ws.send_str(json.dumps({'type': 'pong'}))
                    except json.JSONDecodeError:
                        await ws.send_str(json.dumps({
                            'type': 'error',
                            'message': 'Invalid JSON'
                        }))
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f'WebSocket error: {ws.exception()}')
                    
        except Exception as e:
            logger.error(f"WebSocket handler error: {e}")
        finally:
            # Remove WebSocket client
            session.remove_client(client_id)
        
        return ws
    except Exception as e:
        logger.error(f"Failed to setup WebSocket: {e}")
        return web.json_response(
            {'error': f'Failed to setup WebSocket: {str(e)}'}, 
            status=500
        )

def setup_termisol_routes(app: web.Application):
    """Setup Termisol terminal API routes"""
    # Terminal management routes
    app.router.add_post('/api/termisol/create', create_termisol_terminal)
    app.router.add_get('/api/termisol/list', list_termisol_terminals)
    app.router.add_get('/api/termisol/{terminal_id}', get_termisol_terminal_info)
    app.router.add_post('/api/termisol/{terminal_id}/write', write_to_termisol_terminal)
    app.router.add_post('/api/termisol/{terminal_id}/resize', resize_termisol_terminal)
    app.router.add_post('/api/termisol/{terminal_id}/close', close_termisol_terminal)
    app.router.add_post('/api/termisol/{terminal_id}/features', update_terminal_features)
    
    # Streaming routes
    app.router.add_get('/api/termisol/{terminal_id}/stream', stream_termisol_output)
    app.router.add_get('/api/termisol/{terminal_id}/ws', termisol_websocket_handler)
    
    logger.info("Termisol terminal routes registered")
