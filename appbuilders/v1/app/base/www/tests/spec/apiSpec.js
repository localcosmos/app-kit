describe("api", function() {

	it("initial tenant url should be null", function() {
		expect(api.tenant_api_url).toEqual(null);
	});

	// test tenant api endpoints
	it("should be able to query server for tenant api url", function (done) {
		
		api.construct_api_url("tenant", "test/", "JSON", function(tenant_api_url){

			var expected_url_suffix = "test/?format=JSON";
			
			// check that the suffix is contained by the api url
			expect(tenant_api_url.indexOf(expected_url_suffix)).not.toEqual(-1);

			// check the protocol
			expect(tenant_api_url.substring(0,6)).toEqual(settings["API_URL"].substring(0,6));

			// check if api.tenant_api_url has been set
			expect(api.tenant_api_url).toEqual(tenant_api_url.replace(expected_url_suffix, ""));

			done();

		}, function(){
			throw new Error("api error");
			done();
		});

	});

});
