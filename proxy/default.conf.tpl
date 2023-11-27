server {
  listen ${LISTEN_PORT};

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

  location / {
    proxy_pass http://backend:9000/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade "$http_upgrade";
    proxy_set_header Connection "upgrade";
    proxy_set_header X-Real-IP "$remote_addr";
    proxy_set_header X-Forwarded-For "$proxy_add_x_forwarded_for";
    proxy_set_header X-Forwarded-Proto "$scheme";
    proxy_buffers 16 32k;
    proxy_buffer_size 64k;
  }
}
