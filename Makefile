.PHONY: install

.PHONY: aws-whoami
aws-whoami:
	aws iam get-user

.PHONY: create-aws-components
create-aws-components: aws-whoami
	# creating role...
	aws iam create-role --role-name helpmanual --assume-role-policy-document file://iam-policy/trust.json
	# creating policy...
	aws iam put-role-policy --role-name helpmanual --policy-name helpmanual-perms --policy-document file://iam-policy/permissions.json
	# creating instance profile...
	aws iam create-instance-profile --instance-profile-name helpmanual-profile
	aws iam add-role-to-instance-profile --instance-profile-name helpmanual-profile --role-name helpmanual
	# creating log group...
	aws logs create-log-group --log-group-name helpmanual

.PHONY: create-host
create-host: aws-whoami
	@echo "region: $(AWS_DEFAULT_REGION)"
	docker-machine create --driver amazonec2 --amazonec2-iam-instance-profile helpmanual-profile helpmanual

.PHONY: deploy
deploy:
	./deploy/deploy
