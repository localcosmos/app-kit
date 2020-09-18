"use strict";
/*
* mango is for clients. the whole password stuff is only stored and maintained on the server
*/

var AnonymousUser = {
    id : null,
    pk : null,
    username : '',
    is_staff : false,
    is_active : false,
    is_superuser : false,

	create : function(){
		var self = Object.create(this);
		return self;
	},

    save : function(self){
        throw new Error("mango doesn't provide a DB representation for AnonymousUser.");
	},
    remove : function(self) {
        throw new Error("mango doesn't provide a DB representation for AnonymousUser.");
	},
    /*set_password : function (self, raw_password){
        throw new Error("mango doesn't provide a DB representation for AnonymousUser.")
	},
    check_password : function(self, raw_password){
        throw new Error("mango doesn't provide a DB representation for AnonymousUser.")
	},*/

    is_anonymous : true,

    is_authenticated : false,

    get_username : function (self){
		return self.username;
	}
};


var BaseUser = {

    is_anonymous : false,

    is_authenticated : true,

	get_username : function (self){
		return self.username;
	}

};
