const mongoose = require('mongoose');

const mealSchema = new mongoose.Schema({
  userId: { type: mongoose.Schema.Types.ObjectId, ref: 'User' },
  startTime: Date,
  endTime: Date,
  date: Date,
  transcript: String,
  conversationSuggestions: [String],
  ingredientSuggestions: [String]
});

module.exports = mongoose.model('Meal', mealSchema);