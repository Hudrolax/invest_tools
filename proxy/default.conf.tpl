server {
  listen ${LISTEN_PORT};
  access_log off;

  location /static {
    alias /vol/static;
  }

  location /adminer {
    proxy_pass http://adminer:8080;
    proxy_http_version 1.1;
    proxy_set_header Upgrade "$http_upgrade";
    proxy_set_header Connection "upgrade";
    proxy_set_header X-Real-IP "$remote_addr";
    proxy_set_header X-Forwarded-For "$proxy_add_x_forwarded_for";
    proxy_set_header X-Forwarded-Proto "$scheme";
    proxy_buffers 16 32k;
    proxy_buffer_size 64k;
  }

  location /api/v2/ {
    proxy_pass http://backend:9000/;
    proxy_http_version 1.1;
    proxy_set_header upgrade "$http_upgrade";
    proxy_set_header connection "upgrade";
    proxy_set_header x-real-ip "$remote_addr";
    proxy_set_header x-forwarded-for "$proxy_add_x_forwarded_for";
    proxy_set_header x-forwarded-proto "$scheme";
    proxy_buffers 16 32k;
    proxy_buffer_size 64k;
  }
}
