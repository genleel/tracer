from django.conf import settings
from qcloud_cos import CosConfig, CosS3Client


def create_bucket(bucket, region="ap-beijing"):
    """
    创建桶
    :param bucket: 桶名称
    :param region: 区域
    :return:
    """

    config = CosConfig(Region=region, SecretId=settings.TENCENT_COS_ID, SecretKey=settings.TENCENT_COS_KEY)
    client = CosS3Client(config)
    client.create_bucket(
        Bucket=bucket,
        ACL="public-read"  # private  /  public-read / public-read-write
    )
    # 跨域处理
    cors_config = {
        'CORSRule': [
            {
                'AllowedOrigin': '*',
                'AllowedMethod': ['GET', 'PUT', 'HEAD', 'POST', 'DELETE'],
                'AllowedHeader': "*",
                'ExposeHeader': "*",
                'MaxAgeSeconds': 500
            }
        ]
    }
    client.put_bucket_cors(
        Bucket=bucket,
        CORSConfiguration=cors_config
    )


def upload_file(bucket, region, file_object, key):
    config = CosConfig(Region=region, SecretId=settings.TENCENT_COS_ID, SecretKey=settings.TENCENT_COS_KEY)
    client = CosS3Client(config)

    response = client.upload_file_from_buffer(
        Bucket=bucket,
        Body=file_object,  # 文件对象
        Key=key  # 上传到桶之后的文件名
    )

    return "https://{}.cos.{}.myqcloud.com/{}".format(bucket, region, key)


def delete_file(bucket, region, key):
    config = CosConfig(Region=region, SecretId=settings.TENCENT_COS_ID, SecretKey=settings.TENCENT_COS_KEY)
    client = CosS3Client(config)

    client.delete_object(
        Bucket=bucket,
        Key=key  # 上传到桶之后的文件名
    )


def delete_file_list(bucket, region, key_list):
    config = CosConfig(Region=region, SecretId=settings.TENCENT_COS_ID, SecretKey=settings.TENCENT_COS_KEY)
    client = CosS3Client(config)
    objects = {
        "Quiet": "true",
        "Object": key_list
    }
    client.delete_objects(
        Bucket=bucket,
        Delete=objects
    )


def credential(bucket, region):
    """ 获取cos上传临时凭证 """

    from sts.sts import Sts

    config = {
        # 临时密钥有效时长，单位是秒（30分钟=1800秒）
        'duration_seconds': 10,
        # 固定密钥 id
        'secret_id': settings.TENCENT_COS_ID,
        # 固定密钥 key
        'secret_key': settings.TENCENT_COS_KEY,
        # 换成你的 bucket
        'bucket': bucket,
        # 换成 bucket 所在地区
        'region': region,
        # 这里改成允许的路径前缀，可以根据自己网站的用户登录态判断允许上传的具体路径
        # 例子： a.jpg 或者 a/* 或者 * (使用通配符*存在重大安全风险, 请谨慎评估使用)
        'allow_prefix': '*',
        # 密钥的权限列表。简单上传和分片需要以下的权限，其他权限列表请看 https://cloud.tencent.com/document/product/436/31923
        'allow_actions': [
            # "name/cos:PutObject",
            # 'name/cos:PostObject',
            # 'name/cos:DeleteObject',
            # "name/cos:UploadPart",
            # "name/cos:UploadPartCopy",
            # "name/cos:CompleteMultipartUpload",
            # "name/cos:AbortMultipartUpload",
            "*",
        ],

    }

    sts = Sts(config)
    result_dict = sts.get_credential()
    return result_dict


def check_file(bucket, region, key):
    config = CosConfig(Region=region, SecretId=settings.TENCENT_COS_ID, SecretKey=settings.TENCENT_COS_KEY)
    client = CosS3Client(config)

    data = client.head_object(
        Bucket=bucket,
        Key=key  # 上传到桶之后的文件名
    )

    return data
