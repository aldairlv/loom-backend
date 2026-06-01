# 📋 Plan de Migración: Endpoints de Relationships

**Fecha**: 2026-05-31
**Status**: ✅ Implementado

---

## 🎯 Objetivo

Reemplazar los endpoints de `/relationships/` por una semántica más clara y RESTful bajo `/me/` y `/users/`.

---

## 📊 Mapeo de Endpoints

| Acción | Endpoint Legacy | ✨ Nuevo Endpoint | Método | Status |
|--------|-----------------|-------------------|--------|--------|
| Seguir a un usuario | `POST /v1/relationships/follow/` (body: `{to_profile_id}`) | `POST /v1/users/{user_id}/followers/` | POST | ✅ Implementado |
| Dejar de seguir | `DELETE /v1/relationships/unfollow/{profile_id}/` | `DELETE /v1/users/{user_id}/followers/` | DELETE | ✅ Implementado |
| Listar mis seguidores | `GET /v1/relationships/followers/` | `GET /v1/me/followers/` | GET | ✅ Implementado |
| Listar mis seguidos | `GET /v1/relationships/following/` | `GET /v1/me/following/` | GET | ✅ Implementado |
| Listar mis amigos | `GET /v1/relationships/friends/` | `GET /v1/me/friends/` | GET | ✅ Implementado |

---

## 🔧 Cambios Implementados

### 1. **Nueva Vistas en `relationships/views.py`**
   - `MeFollowersView` → Lista de seguidores
   - `MeFollowingView` → Lista de seguidos
   - `MeFriendsView` → Lista de amigos
   - `UserFollowersCreateView` → Seguir a un usuario
   - `UserFollowersDestroyView` → Dejar de seguir

### 2. **Registradas en `apps/api/urls_v1.py`**
   ```python
   path('me/followers/', MeFollowersView.as_view()),
   path('me/following/', MeFollowingView.as_view()),
   path('me/friends/', MeFriendsView.as_view()),
   path('users/<uuid:user_id>/followers/', UserFollowersCreateView.as_view()),
   path('users/<uuid:user_id>/followers/', UserFollowersDestroyView.as_view()),
   ```

### 3. **Endpoints Legacy (Mantienen Compatibilidad)**
   - Siguen disponibles en `/v1/relationships/`
   - Reutilizan las mismas vistas (sin duplicación de lógica)
   - Marcadas como **deprecated** en documentación

---

## 📝 Ventajas de la Nueva Estrategia

✅ **Mejor Semántica**: `/me/` claramente es para el usuario autenticado  
✅ **RESTful**: `/users/{id}/followers/` sigue patrones REST estándar  
✅ **Sin Duplicación**: Reutiliza servicios existentes  
✅ **Backwards Compatible**: Los viejos endpoints siguen funcionando  
✅ **Plan de Migración Claro**: Los clientes tienen tiempo de migrar  

---

## 🚀 Plan de Deprecación (Recomendado)

### Fase 1 (Ahora - v1.0)
- ✅ Nuevos endpoints disponibles
- Viejos endpoints funcionan (sin cambios)
- Documentación: Marcar viejos como "deprecated"

### Fase 2 (v1.1 - 2-3 meses)
- Agregar headers `Deprecation: true` en respuestas de endpoints viejos
- Actualizar SDK/Ejemplos de clientes a nuevos endpoints

### Fase 3 (v2.0)
- Remover endpoints legacy completamente

---

## 🧪 Testing

Para verificar que todo funciona:

```bash
# Test: Seguir a un usuario (nuevo)
curl -X POST http://localhost:8000/api/v1/users/{user_id}/followers/ \
  -H "Authorization: Bearer {token}"

# Test: Listar mis seguidos (nuevo)
curl -X GET http://localhost:8000/api/v1/me/following/ \
  -H "Authorization: Bearer {token}"

# Test: Viejos endpoints aún funcionan
curl -X GET http://localhost:8000/api/v1/relationships/following/ \
  -H "Authorization: Bearer {token}"
```

---

## 📚 Cambios en el Cliente (Próximo Paso)

Actualizar frontend/SDK para usar:
```javascript
// OLD ❌
POST /api/v1/relationships/follow/ 
body: { to_profile_id: "uuid" }

// NEW ✅
POST /api/v1/users/{userId}/followers/
```

---

## 📖 Referencia Rápida

| Antiguo | Nuevo |
|---------|-------|
| `relationships/follow/` | `users/{id}/followers/` (POST) |
| `relationships/unfollow/{id}/` | `users/{id}/followers/` (DELETE) |
| `relationships/followers/` | `me/followers/` |
| `relationships/following/` | `me/following/` |
| `relationships/friends/` | `me/friends/` |
