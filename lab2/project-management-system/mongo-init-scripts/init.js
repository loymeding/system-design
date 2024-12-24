// ./mongo-init-scripts/init.js
db.createUser({
  user: 'mongoadmin',
  pwd: 'mongopass',
  roles: [
      {
          role: 'readWrite',
          db: 'service_service'
      },
      {
          role: 'dbAdmin',
          db: 'service_service'
      }
  ]
});

db = db.getSiblingDB('service_service');

// Create collections
db.createCollection('services');

// Create indexes
db.services.createIndex({ "order_id": 1 });
db.services.createIndex({ "creator_id": 1 });
db.services.createIndex({ "assignee_id": 1 });
db.services.createIndex({ "cost": 1 });
db.services.createIndex({
  "order_id": 1
});
db.services.createIndex({ "created_at": -1 });
db.services.createIndex({ "tags": 1 });