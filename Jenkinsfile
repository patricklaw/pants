

def shards = [:]

def ciShShardedNode(os, flags, typeFlag, shardNum, totalShards) {
  { ->
    node(os) {
      checkout scm
      sh "./build-support/bin/ci.sh ${flags} ${typeFlag} ${shardNum}/${totalShards}"
    }
  }
}

def ciShNode(os, flags) {
  { ->
    node(os) {
      checkout scm
      sh "./build-support/bin/ci.sh ${flags}"
    }
  }
}

def allOSes = ["linux", "osx"]
for (int i = 0; i < allOSes.size(); i++) {
  def os = allOSes.get(i)

  shards["${os}_self-checks"] = ciShNode(os, '-cjlpn')
  shards["${os}_contrib"] = ciShNode(os, '-fkmsrcjlp')

  def totalShards = 10
  for (int shardNum = 0; shardNum < totalShards; shardNum++) {
    def oneIndexed = shardNum + 1
    shards["${os}_unit_tests_${oneIndexed}_of_10"] = ciShShardedNode(
      os, '-fkmsrcn', '-u', shardNum, totalShards
    )
    shards["${os}_integration_tests_${oneIndexed}_of_10"] = ciShShardedNode(
      os, '-fkmsrjlpn', '-i', shardNum, totalShards
    )
  }
}

parallel shards
