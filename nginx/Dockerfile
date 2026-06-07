FROM nginx:alpine

# Remove default configuration file
RUN rm /etc/nginx/conf.d/default.conf

# Copy our custom configuration file
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
