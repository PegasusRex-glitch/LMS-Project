# Use official Node.js LTS image
FROM node:18-alpine

# Set working directory
WORKDIR /usr/src/app


# Copy package.json and package-lock.json
COPY package*.json ./

# Install dependencies, including dotenv
RUN npm install dotenv && npm install --production

# Copy the rest of the application code
COPY . .

# Expose port (change if your app uses a different port)
EXPOSE 3000

# Start the server
CMD ["node", "server.js"]
FROM node:18

WORKDIR /app

COPY package.json .
RUN npm install

COPY . .

EXPOSE 5000

CMD ["node", "server.js"]