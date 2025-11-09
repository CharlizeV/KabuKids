const mongoose = require('mongoose');

const userSchema = new mongoose.Schema({
  name: String,
  username: String,
  password: String,
  age: Number,
  birthday: Date,
  likes: [String],
  dislikes: [String]
});

module.exports = mongoose.model('User', userSchema);