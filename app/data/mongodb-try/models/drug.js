var mongoose = require('mongoose');
var Schema = mongoose.Schema;

var DrugSchema = new Schema ({
  dose: {
    value: {
      type: Number,
      required: true
    },
    unit: {
      type: String,
      require: true
    }
  },
  price: {
    type: Number,
    required: true
  },
  name: {
    type: String,
    required: true
  },
  dclass: {
    type: Schema.Types.ObjectId,
    ref: 'Class'
  }
});

module.exports = mongoose.model('Drug', DrugSchema);