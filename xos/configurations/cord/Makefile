MYIP:=$(shell hostname -i)
RUNNING_CONTAINER:=$(shell sudo docker ps|grep "xos"|awk '{print $$NF}')
LAST_CONTAINER=$(shell sudo docker ps -l -q)

cord: common_cloudlab ceilometer_dashboard virtualbng_json
	rm ../../xos_configuration/*
	echo "# Autogenerated -- do not edit" > Dockerfile
	cat ../common/Dockerfile.common Dockerfile.cord >> Dockerfile
	cp ../common/xos_common_config ../../xos_configuration/
	cp ./xos_cord_config ../../xos_configuration/
	cd ../../..; sudo docker build -t xos -f xos/configurations/cord/Dockerfile .
	sudo docker run -d --add-host="ctl:$(MYIP)" -p 9999:8000 xos
	bash ../common/wait_for_xos.sh

common_cloudlab:
	make -C ../common -f Makefile.cloudlab

ceilometer_dashboard:
	#NOTE: The below dashboard install scripts assume 
	#clouldlab openstack environment created using "OpenStack" profile
	bash install_xos_ceilometer_dashboard.sh
	bash install_ceilometer_patch.sh

virtualbng_json:
	bash make-virtualbng-json.sh

stop:
	sudo docker stop $(RUNNING_CONTAINER)

showlogs:
	sudo docker logs $(LAST_CONTAINER)

enter:
	sudo docker exec -t -i $(RUNNING_CONTAINER) bash
