/* public/js/api.js – ES-module con helpers a la API Flask */
export const API = {
    /* ---------- AUTH ---------- */
    login({ email, password }) {
      return fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      }).then(r => r.json());
    },
    me()     { return fetch('/api/me').then(r => r.json()); },
    logout() { return fetch('/api/logout').then(r => r.json()); },
  
    /* ---------- USERS ---------- */
    listUsers() {
      return fetch('/api/users').then(r => r.json());
    },
    updateUser(id, data) {                       // ← id = user_id
      return fetch(`/api/users/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      }).then(r => r.json());
    },
    deleteUser(id) {                             // ← id = user_id
      return fetch(`/api/users/${id}`, {
        method: 'DELETE'
      }).then(r => r.json());
    },
  
    /* ---------- PRODUCTS ---------- */
    listProducts() {
      return fetch('/api/products').then(r => r.json());
    },
    createProduct(data) {
      return fetch('/api/products', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      }).then(r => r.json());
    },
    updateProduct(id, data) {
      return fetch(`/api/products/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      }).then(r => r.json());
    },
    deleteProduct(id) {
      return fetch(`/api/products/${id}`, { method: 'DELETE' })
             .then(r => r.json());
    },
  
    /* ---------- CART ---------- */
    listCart() {
      return fetch('/api/cart').then(r => r.json());
    },
    addToCart(product_id, qty = 1) {
      return fetch('/api/cart', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ product_id, qty })
      }).then(r => r.json());
    },
    removeFromCart(product_id) {
      return fetch(`/api/cart/${encodeURIComponent(product_id)}`, {
        method: 'DELETE'
      }).then(r => r.json());
    },
  
    /* ---------- CHECKOUT ---------- */
    checkout() {
      return fetch('/api/checkout', { method: 'POST' })
             .then(r => r.json());
    },
  
    /* ---------- ORDERS ---------- */
    listOrders() {
      return fetch('/api/orders').then(r => r.json());
    }
  };
  