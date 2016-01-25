var mongoose = require('mongoose');
var Schema = mongoose.Schema;

var ClassSchema = new Schema ({
  name : {
    type: String,
    required: true
  }
});

module.exports = mongoose.model('Class', ClassSchema);