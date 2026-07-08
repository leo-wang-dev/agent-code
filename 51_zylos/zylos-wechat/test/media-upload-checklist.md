# Media Upload Review Checklist

## getUploadUrl
- [ ] `filekey`: 32-char hex, unique per upload
- [ ] `media_type`: correct mapping (1=IMAGE, 2=VIDEO, 3=FILE, 4=VOICE)
- [ ] `to_user_id`: valid recipient
- [ ] `rawsize`: plaintext byte count (not ciphertext)
- [ ] `rawfilemd5`: hex MD5 of plaintext
- [ ] `filesize`: ciphertext byte count (`ceil((rawsize+1)/16)*16`)
- [ ] `no_need_thumb`: true
- [ ] `aeskey`: 32-char hex of 16-byte key (raw hex, not base64)
- [ ] `base_info.channel_version` included

## CDN Upload
- [ ] URL: `<cdnBaseUrl>/upload?encrypted_query_param=<urlenc(upload_param)>&filekey=<urlenc(filekey)>`
- [ ] Content-Type: `application/octet-stream`
- [ ] Body: AES-128-ECB encrypted data (PKCS7 padding)
- [ ] Response header `x-encrypted-param` captured as `downloadParam`
- [ ] 4xx → abort immediately (no retry)
- [ ] 5xx / network error → retry up to 3 times

## sendMessage media item
- [ ] Image (type=2): `image_item.media.encrypt_query_param`, `aes_key`, `encrypt_type=1`, `mid_size`
- [ ] File (type=4): `file_item.media.*`, `file_name`, `len` (plaintext bytes as string)
- [ ] Video (type=5): `video_item.media.*`, `video_size`
- [ ] `aes_key` encoding: `base64(hex-string-of-aeskey-bytes)` — NOT `base64(raw-bytes)`
- [ ] `context_token` present
- [ ] `client_id` unique

## Decrypt roundtrip
- [ ] `encrypt(plaintext, key)` → ciphertext → `decrypt(ciphertext, key)` === plaintext
- [ ] MD5 of decrypted matches original `rawfilemd5`
- [ ] Key encoding roundtrip: `encodeAesKeyForMessage(key)` → `decodeAesKey(encoded)` === key

## Error paths
- [ ] `ERR_WECHAT_UPLOAD_URL`: getUploadUrl fails (ret !== 0)
- [ ] `ERR_WECHAT_CDN_UPLOAD`: CDN returns non-200
- [ ] `ERR_WECHAT_CDN_NO_PARAM`: x-encrypted-param header missing
- [ ] `ERR_WECHAT_SEND_MEDIA`: sendMessage with media item fails
